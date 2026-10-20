"""Hash-pinned BOM source assertion conformance; units/currency are explicit test declarations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from procurement_intelligence_lab.bootstrap import build_bom_assertion_service
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from tools.benchmark_bom_stages import AT, ROOT, checkout_revision, digest

DEFAULT_MANIFEST = ROOT / "evals/extraction/bom-assertions-v1/manifest.json"


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
            "bom-assertions-conformance",
            "bom-assertions",
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
            result = build_bom_assertion_service(
                captured_at=AT, context=context, policy=policy
            ).run(source)
        except SemanticContractError as exc:
            records.append({"path": item["path"], "outcome": "failed", "failure": exc.as_dict()})
            continue
        observations = sorted(
            [
                [
                    x.context.observation.observation_key,
                    x.predicate.value,
                    str(x.value) if x.value is not None else None,
                    x.context.observation.unit,
                    x.context.observation.status.value,
                    x.context.observation.diagnostic,
                    x.context.observation.source_field.raw_value,
                    x.evidence.sheet,
                    x.evidence.row,
                    list(x.evidence.cells),
                ]
                for x in result.assertions
            ],
            key=lambda x: x[0],
        )
        mentions = sorted(
            [
                [
                    x.assertions[0].evidence.row,
                    x.text,
                    sorted(a.context.observation.observation_key for a in x.assertions),
                ]
                for x in result.mentions
            ],
            key=lambda x: x[0],
        )
        layer = {"count": len(observations), "sha256": digest(observations)}
        mention_layer = {"count": len(mentions), "sha256": digest(mentions)}
        checks = {
            "assertions": layer == item["expected"],
            "mentions": mention_layer == item["mentions"],
            "evidence_identity": all(
                x.evidence.artifact_id == result.origin.artifact.artifact_id
                and x.evidence.content_hash == source_hash
                for x in result.assertions
            ),
            "attached_observations": tuple(x.context.observation for x in result.assertions)
            == result.normalized.observations,
            "origin_and_provenance": all(
                x.context.origin == result.origin
                and x.context.provenance == result.provenance
                and x.context.confidence_diagnostic == "not estimated"
                and x.transformation_event_id == result.normalized.transformation.event_id
                for x in result.assertions
            ),
            "unique_ids": len({x.assertion_id for x in result.assertions})
            == len(result.assertions),
            "five_stages": len(result.as_dict()["transformations"]) == 5,
        }
        records.append(
            {
                "path": item["path"],
                "source_hash": source_hash,
                "assertions": layer,
                "mentions": mention_layer,
                "checks": checks,
                "outcome": "passed" if all(checks.values()) else "failed",
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        )
    checkout_revision(revision)
    return {
        "schema_version": 1,
        "kind": "deterministic-bom-assertions-conformance",
        "revision": revision,
        "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "policy": policy.as_dict(),
        "sources": records,
        "passed": bool(records) and all(r["outcome"] == "passed" for r in records),
        "inference_calls": 0,
        "inference_cost_usd": "0",
        "compute_cost_usd": None,
        "limit": "Nine synthetic BOM sources; explicit test declarations, no inferred units/currency or provider/model comparison; source assertions only; no resolution, authority, ledger persistence or downstream runtime claim.",
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
