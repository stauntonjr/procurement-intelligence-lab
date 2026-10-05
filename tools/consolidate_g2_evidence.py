"""Offline G2 evidence dossier and opt-in deterministic HTTP timing; no inference."""

import argparse
import json
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

from tools import evaluate_procurement_corpus as corpus
from tools.g2_evidence import REQUIRED_SUITE, ROLES, compile_report, timing
from tools.run_g2_pilot import installed_inspector


def empty_group(reason: str, status: str = "unknown") -> dict[str, Any]:
    return {
        "evidence_status": status,
        "errors": [reason],
        "counts": None,
        "real_model_attempts": None,
        "controlled_protocol_attempts": None,
        "tool_starts": None,
        "saves": None,
        "cost_observed_usd": None,
    }


def read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 2_000_000:
        raise ValueError("bounded_report_size")

    def invalid(value: str):
        raise ValueError("nonfinite_json")

    value: dict[str, Any] = json.loads(path.read_text(), parse_constant=invalid)
    if type(value) is not dict:
        raise TypeError("object_required")
    return value


def consolidate(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    reports: dict[str, Any] = manifest.get("reports", {})
    valid_manifest = (
        manifest.get("schema_version") == 1
        and type(reports) is dict
        and not set(reports) - set(ROLES)
    )
    groups: dict[str, Any] = {}
    for role in ROLES:
        spec: dict[str, Any] | None = reports.get(role) if type(reports) is dict else None
        if not spec or not valid_manifest:
            groups[role] = empty_group(
                "missing_manifest_role" if valid_manifest else "invalid_manifest"
            )
            continue
        try:
            relative = Path(spec["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("artifact_escape")
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("artifact_escape")
            if path.stat().st_size > 2_000_000:
                raise ValueError("bounded_report_size")
            if sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
                raise ValueError("artifact_hash_mismatch")
            if (
                not spec["ids"]
                or len(set(spec["ids"])) != len(spec["ids"])
                or not all(type(i) is str and i for i in spec["ids"])
            ):
                raise ValueError("invalid_denominator")
            denominators = {
                "fresh_language": 48,
                "original_browser": 9,
                "adversarial": 9,
                "baseline_controls": 28,
                "candidate_controls": 28,
                "deterministic_baseline": 48,
            }
            if len(spec["ids"]) != denominators[role]:
                raise ValueError("changed_denominator")
            target = manifest["target_versions"]
            if role not in ("baseline_controls", "original_browser") and spec["versions"] != target:
                raise ValueError("incompatible_target")
            if role == "original_browser" and any(
                any(v[k] != target[k] for k in target if k != "fixture")
                for v in spec["versions"].values()
            ):
                raise ValueError("incompatible_target")
            groups[role] = compile_report(role, read_json(path), spec) | {
                "artifact": spec["path"],
                "sha256": spec["sha256"],
                "expected_cases": len(spec["ids"]),
                "use": spec["use"],
            }
        except FileNotFoundError:
            groups[role] = empty_group("missing_artifact")
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            groups[role] = empty_group(
                str(error) if type(error) is ValueError else type(error).__name__, "fail"
            )
    ready = valid_manifest and all(g["evidence_status"] == "pass" for g in groups.values())
    ready = ready and all(
        groups[role]["counts"]["pass"] == groups[role]["expected_cases"] for role in REQUIRED_SUITE
    )
    return {
        "schema_version": 1,
        "target_versions": manifest.get("target_versions"),
        "groups": groups,
        "bounded_installed_suite_ready": bool(ready),
        "release_ready": False,
        "remaining_gates": {
            name: "unknown"
            for name in (
                "comprehensive_browser_accessibility_and_error_recovery",
                "deployed_agent_walkthrough",
                "measured_five_minute_presentation_or_recording",
                "integration_to_main",
                "broader_issue_layer_metrics",
            )
        },
        "limits": "Pinned historical evidence, not a new inference or general accuracy run. Populations/timing scopes remain separate; controlled protocol is not model quality. Costs unobserved/null. Full G2/release/B2 expansion not ready.",
    }


def measure_baseline(python: Path, dataset: Path) -> dict[str, Any]:
    queries = corpus.load_dataset(dataset)["queries"]
    investigation: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    script = (
        "import json,tempfile;from pathlib import Path;from dataclasses import asdict;"
        "from procurement_intelligence_lab.interfaces.live_review import compose_live;"
        'print(json.dumps(asdict(compose_live(Path(tempfile.mkdtemp())/"probe.db").runs.versions)))'
    )
    versions = json.loads(
        subprocess.check_output(
            [str(python.absolute()), "-c", script], cwd="/tmp", text=True, timeout=20
        )
    )

    def measured(url: str):
        began = time.monotonic()
        status = None
        try:
            try:
                with urlopen(url, timeout=20) as response:
                    status, value = response.status, json.load(response)
            except HTTPError as error:
                status, value = error.code, json.load(error)
            return status, value
        finally:
            row: dict[str, Any] = {"status": status, "seconds": time.monotonic() - began}
            if "/api/corpus/investigate?" in url:
                row["id"] = queries[len(investigation)]["id"]
                investigation.append(row)
            else:
                sources.append(row)

    with installed_inspector(python) as base_url:
        structured = corpus.evaluate(base_url, dataset, fetch=measured)
    return {
        "schema_version": 1,
        "versions": versions,
        "structured": structured,
        "investigation_requests": investigation,
        "source_requests": sources,
        "investigation_http_seconds": timing([r["seconds"] for r in investigation]),
        "source_http_seconds": timing([r["seconds"] for r in sources]),
        "condition": "One sequential run in fresh installed inspector process. OS/cache warm/cold state unmeasured; HTTP roundtrip includes admission and serialization. Structured oracle inputs; no natural-language interpretation, model calls, human review or saves. Source lookups measured separately.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("evals/operational_agents/g2-evidence-v1.json")
    )
    parser.add_argument("--artifact-root", type=Path, default=Path.cwd())
    parser.add_argument("--measure-baseline", action="store_true")
    parser.add_argument("--python", type=Path)
    parser.add_argument("--dataset", type=Path, default=corpus.DATASET)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required; never overwrite evidence")
    if args.measure_baseline:
        if args.python is None:
            parser.error("--python required for installed baseline")
        report = measure_baseline(args.python, args.dataset)
        ready = report["structured"]["ready"]
    else:
        try:
            manifest = read_json(args.manifest)
        except (OSError, ValueError, TypeError):
            manifest = {}
        report = consolidate(manifest, args.artifact_root)
        ready = report["bounded_installed_suite_ready"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        "baseline_ready" if args.measure_baseline else "bounded_installed_suite_ready", bool(ready)
    )
    return int(not ready)


if __name__ == "__main__":
    raise SystemExit(main())
