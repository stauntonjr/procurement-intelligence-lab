"""Hash-pinned BOM normalization conformance; units/currency are explicit test declarations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from procurement_intelligence_lab.bootstrap import build_bom_normalization_service
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from tools.benchmark_bom_stages import AT, ROOT, checkout_revision, digest

DEFAULT_MANIFEST = ROOT / "evals/extraction/bom-normalization-v1/manifest.json"


def benchmark(manifest_path: Path, expected_revision: str | None = None) -> dict[str, object]:
    revision = checkout_revision(expected_revision)
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    declaration = manifest["policy"]
    if declaration["profile"] != "bom-decimal@1":
        raise ValueError("unsupported conformance normalization profile")
    policy = BomNormalizationPolicy(
        CountUnit(declaration["quantity_unit"]),
        declaration["currency"],
        CountUnit(declaration["price_unit"]),
    )
    records: list[dict[str, object]] = []
    for item in manifest["sources"]:
        path = ROOT / item["path"]
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if source_hash != item["sha256"]:
            records.append(
                {"path": item["path"], "outcome": "failed", "failure": "source_hash_mismatch"}
            )
            continue
        context = ProvenanceContext(
            "bom-normalization-conformance",
            "bom-normalization",
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
        started = time.perf_counter()
        try:
            result = build_bom_normalization_service(
                captured_at=AT, context=context, policy=policy
            ).run(source)
        except SemanticContractError as exc:
            records.append({"path": item["path"], "outcome": "failed", "failure": exc.as_dict()})
            continue
        observations = sorted(
            [
                [
                    x.observation_key,
                    x.predicate,
                    str(x.value) if x.value is not None else None,
                    x.unit,
                    x.status.value,
                    x.diagnostic,
                    x.source_field.raw_value,
                    x.source_field.evidence.sheet,
                    x.source_field.evidence.row,
                    list(x.source_field.evidence.cells),
                ]
                for x in result.observations
            ],
            key=lambda x: x[0],
        )
        layer = {"count": len(observations), "sha256": digest(observations)}
        checks = {
            "observations": layer == item["expected"],
            "evidence_identity": all(
                x.source_field.evidence.artifact_id == result.stages.artifact.artifact_id
                and x.source_field.evidence.content_hash == source_hash
                for x in result.observations
            ),
            "scope_time": all(
                x.scope == source.scope and x.effective_at == source.observed_at
                for x in result.observations
            ),
            "source_fields": tuple(x.source_field for x in result.observations)
            == result.stages.mapped.fields,
            "unique_ids": len({x.observation_id for x in result.observations})
            == len(result.observations),
        }
        records.append(
            {
                "path": item["path"],
                "source_hash": source_hash,
                "observations": layer,
                "checks": checks,
                "outcome": "passed" if all(checks.values()) else "failed",
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        )
    checkout_revision(revision)
    return {
        "schema_version": 1,
        "kind": "deterministic-bom-normalization-conformance",
        "revision": revision,
        "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "policy": policy.as_dict(),
        "sources": records,
        "passed": bool(records) and all(r["outcome"] == "passed" for r in records),
        "inference_calls": 0,
        "inference_cost_usd": "0",
        "compute_cost_usd": None,
        "limit": "Nine synthetic BOM sources; explicit test declarations, no inferred units/currency or provider/model comparison; no ASSERT or downstream runtime claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--revision", help="Optional exact clean HEAD assertion")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = benchmark(args.manifest, args.revision)
    except (OSError, ValueError, KeyError, TypeError) as exc:
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
