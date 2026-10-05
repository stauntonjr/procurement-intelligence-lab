"""Explicit authorized local inference smoke; fixture calls never enter live aggregates."""

import argparse
import json
import sqlite3
import subprocess
import time
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

from procurement_intelligence_lab.application.corpus_agent_tools import InvestigateToolArgs
from procurement_intelligence_lab.application.exact_brief_review import brief_facts
from procurement_intelligence_lab.interfaces.live_review import compose_live
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true", required=True)
    parser.add_argument(
        "--python", type=Path, required=True, help="Clean installed workflow wheel Python"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evals/operational_agents/local-qwen-walkthrough-v1.json"),
    )
    args = parser.parse_args()
    if args.database.exists():
        raise ValueError("use a fresh acceptance database")
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    report = {
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "label": manifest["split"],
        "execution_kind": "live",
        "runs": [],
        "failures": [],
        "acceptance": "not_ready",
    }

    def retain() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")

    with urlopen("http://127.0.0.1:8000/version", timeout=5) as response:
        report["server"] = json.load(response)
    baseline = compose_live(args.database)
    report["versions"] = asdict(baseline.runs.versions)
    context = RequestContext(
        "local-demo", "synthetic-tenant", "atlas", "lab", frozenset(Permission), "acceptance"
    )
    base = [
        str(args.python.absolute()),
        "-m",
        "procurement_intelligence_lab.interfaces.live_review",
        "--database",
        str(args.database.resolve()),
        "--project",
        "atlas",
    ]

    def invoke(*fields: str) -> dict:
        completed = subprocess.run(
            [*base, *fields], cwd="/tmp", capture_output=True, text=True, timeout=60, check=False
        )
        if completed.returncode:
            raise RuntimeError(
                completed.stdout.strip()
                or "public CLI failed: "
                + (completed.stderr.splitlines()[-1] if completed.stderr else "unknown")
            )
        return json.loads(completed.stdout)

    retain()
    for case in manifest["cases"]:
        request = InvestigateToolArgs.from_mapping(
            {"item": case["item"], "as_of": manifest["as_of"]}
        ).request
        expected = brief_facts(
            baseline.service.tools.investigator.investigate(request, context=context)
        )
        for repetition in range(manifest["repetitions"]):
            began = time.monotonic()
            record = {"case": case["id"], "repetition": repetition + 1, "passed": False}
            try:
                result = invoke("ask", "--question", case["question"], "--as-of", manifest["as_of"])
                record["interpretation"] = result["interpretation"]
                view = result["workflow"]
                if view is None or view["brief"]["content_json"] != expected:
                    raise RuntimeError("intent/facts differ from deterministic baseline")
                brief = view["brief"]
                recovered = invoke("recover", "--run-id", view["run_id"])
                if recovered != result:
                    raise RuntimeError("restart changed exact pending brief")
                for ref in json.loads(expected)["evidence"]:
                    source = baseline.reader.source_by_id(ref["evidence_id"], context=context)
                    if source.evidence.evidence_id != ref["evidence_id"]:
                        raise RuntimeError("unresolvable evidence")
                bad = subprocess.run(
                    [
                        *base,
                        "review",
                        "--run-id",
                        view["run_id"],
                        "--brief-id",
                        brief["brief_id"],
                        "--digest",
                        "0" * 64,
                        "--decision",
                        "approve",
                    ],
                    cwd="/tmp",
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if bad.returncode != 1:
                    raise RuntimeError("altered approval accepted")
                fields = (
                    "review",
                    "--run-id",
                    view["run_id"],
                    "--brief-id",
                    brief["brief_id"],
                    "--digest",
                    brief["digest"],
                    "--decision",
                    "approve",
                )
                saved = invoke(*fields)
                if saved["status"] != "completed" or invoke(*fields) != saved:
                    raise RuntimeError("review/save not idempotent")
                record.update(
                    {
                        "passed": True,
                        "facts": json.loads(expected),
                        "saved_result_id": saved["saved"]["saved_id"],
                        "model_calls": 1,
                        "tool_calls": sum(
                            e.kind.value == "tool_started"
                            for e in baseline.runs.events(view["run_id"], context=context)
                        ),
                    }
                )
            except (RuntimeError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
                record["failure"] = str(error)
                report["failures"].append(
                    {"case": case["id"], "repetition": repetition + 1, "failure": str(error)}
                )
            record["public_roundtrip_seconds"] = time.monotonic() - began
            report["runs"].append(record)
            retain()
            print(case["id"], repetition + 1, "PASS" if record["passed"] else "FAIL", flush=True)
    report["abstentions"] = []
    for case in manifest["abstentions"]:
        result = invoke("ask", "--question", case["question"], "--as-of", manifest["as_of"])
        call = result["interpretation"]
        events = baseline.runs.events(call["run_id"], context=context)
        passed = (
            call["status"] == case["status"] and result["workflow"] is None and len(events) == 1
        )
        report["abstentions"].append({"case": case["id"], "passed": passed, "interpretation": call})
        if not passed:
            report["failures"].append(
                {"case": case["id"], "failure": "abstention or no-tool gate failed"}
            )
        retain()
        print(case["id"], "PASS" if passed else "FAIL", flush=True)
    with sqlite3.connect(args.database) as db:
        report["saved_results"] = db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0]
    report["acceptance"] = (
        "bounded_cli_walkthrough_passed" if not report["failures"] else "not_ready"
    )
    report["limits"] = (
        "Development corpus walkthroughs only; no broad accuracy, original fixture live routing, browser/deployment, hard cancellation or G2 held-out acceptance. Source resolution uses the installed application's matching admitted inventory; authenticated source HTTP has separate contract coverage."
    )
    retain()
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
