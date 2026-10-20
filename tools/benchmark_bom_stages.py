"""Hash-pinned deterministic structure/mapping conformance; no model comparison claim."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from procurement_intelligence_lab.bootstrap import build_bom_stage_service
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "evals/extraction/bom-stages-v1/manifest.json"
AT = datetime(2026, 10, 19, tzinfo=UTC)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def checkout_revision(expected: str | None = None) -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.PIPE
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("conformance context requires a readable Git checkout") from exc
    if expected is not None and expected != revision:
        raise ValueError("conformance context revision does not match checkout HEAD")
    if dirty:
        raise ValueError("conformance context requires a clean tracked and untracked worktree")
    if (
        Path(inspect.getfile(build_bom_stage_service)).resolve()
        != (ROOT / "src/procurement_intelligence_lab/bootstrap.py").resolve()
    ):
        raise ValueError("conformance context imported code from outside the verified checkout")
    return revision


def benchmark(manifest_path: Path, revision: str | None = None) -> dict[str, object]:
    revision = checkout_revision(revision)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    records: list[dict[str, object]] = []
    for item in manifest["sources"]:
        path = ROOT / item["path"]
        started = time.perf_counter()
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != item["sha256"]:
            records.append(
                {"path": item["path"], "outcome": "failed", "failure": "source_hash_mismatch"}
            )
            continue
        context = ProvenanceContext(
            "bom-stage-conformance",
            "bom-stages",
            "1",
            revision,
            "local-uncontainerized",
            digest(item),
            None,
            (),
            AT,
        )
        source = SourceReference(
            "synthetic-conformance", path.as_uri(), StateScope(**item["scope"]), AT, item["sha256"]
        )
        try:
            result = build_bom_stage_service(captured_at=AT, context=context).run(source)
        except SemanticContractError as exc:
            records.append({"path": item["path"], "outcome": "failed", "failure": exc.as_dict()})
            continue
        rows = sorted(
            [
                [e.evidence.row, list(e.evidence.cells)]
                for e in result.structured.elements
                if e.kind == "row"
            ]
        )
        cells = sorted(
            [
                [e.evidence.row, e.evidence.cells[0], e.text]
                for e in result.structured.elements
                if e.kind == "cell"
            ]
        )
        fields = sorted(
            [
                [
                    f.evidence.row,
                    f.field_key.split("!")[1].rstrip("0123456789"),
                    f.field_name,
                    f.raw_value,
                    f.status.value,
                    f.diagnostic,
                ]
                for f in result.mapped.fields
            ]
        )
        field_evidence = sorted(
            [f.field_key, f.evidence.sheet, f.evidence.row, list(f.evidence.cells)]
            for f in result.mapped.fields
        )
        layers = {
            name: {"count": len(values), "sha256": digest(values)}
            for name, values in [
                ("rows", rows),
                ("cells", cells),
                ("fields", fields),
                ("field_evidence", field_evidence),
            ]
        }
        checks = {name: layers[name] == item["expected"][name] for name in layers}
        checks["evidence_identity"] = all(
            evidence.artifact_id == result.artifact.artifact_id
            and evidence.content_hash == actual_hash
            for evidence in [
                *(e.evidence for e in result.structured.elements),
                *(f.evidence for f in result.mapped.fields),
            ]
        )
        records.append(
            {
                "path": item["path"],
                "source_hash": actual_hash,
                "outcome": "passed" if all(checks.values()) else "failed",
                "layers": layers,
                "checks": checks,
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        )
    checkout_revision(revision)
    return {
        "schema_version": 1,
        "kind": "deterministic-bom-stage-conformance",
        "revision": revision,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "sources": records,
        "passed": bool(records) and all(r["outcome"] == "passed" for r in records),
        "inference_calls": 0,
        "inference_cost_usd": "0",
        "compute_cost_usd": None,
        "model_versions": [],
        "prompt_versions": [],
        "limit": "Nine synthetic BOM workbooks only; exact structural/raw mapping conformance, no OCR/provider comparison, business normalization or execution benchmark.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--revision", help="Optional exact HEAD assertion; actual identity is derived from Git"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = benchmark(args.manifest, args.revision)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "source_count": len(report["sources"]),
                "report": str(args.output),
            }
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
