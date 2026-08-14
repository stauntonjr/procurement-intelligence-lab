"""Runnable synthetic BOM evidence demo."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from typing import Any

from procurement_intelligence_lab.adapters.xlsx import read_bom
from procurement_intelligence_lab.application.evidence_service import (
    ClaimKind,
    EvidenceBackedClaim,
    inspect_bom_claims,
)
from procurement_intelligence_lab.application.pipeline import run_bom_pipeline
from procurement_intelligence_lab.domain.bom import Bom, EvidenceRef
from procurement_intelligence_lab.domain.scope import Permission, RequestContext


def _default_bom_path() -> Path:
    return Path(str(files("procurement_intelligence_lab.examples").joinpath("synthetic_bom.xlsx")))


def _evidence_payload(evidence: EvidenceRef) -> dict[str, object]:
    return {
        "artifact_id": evidence.artifact_id,
        "content_hash": evidence.content_hash,
        "sheet": evidence.sheet,
        "row": evidence.row,
        "cells": evidence.cells,
    }


def _query_payload(result: EvidenceBackedClaim) -> dict[str, object]:
    value: object = str(result.value) if isinstance(result.value, Decimal) else result.value
    return {
        "value": value,
        "status": result.status,
        "evidence": [_evidence_payload(item) for item in result.evidence],
    }


def demo_payload(bom: Bom, canonical_candidates: tuple[str, ...]) -> dict[str, Any]:
    pipeline = run_bom_pipeline(bom, canonical_candidates)
    context = RequestContext(
        "cli-user",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset({Permission.READ_STATE}),
        "cli-demo",
    )
    claims = {
        claim.kind: claim
        for claim in inspect_bom_claims(
            bom,
            canonical_candidates,
            request_context=context,
        )
    }
    return {
        "claims": {
            "distinct_skus": _query_payload(claims[ClaimKind.DISTINCT_SKUS]),
            "gpu_quantity": _query_payload(claims[ClaimKind.GPU_QUANTITY]),
            "bom_cost": _query_payload(claims[ClaimKind.BOM_COST]),
        },
        "operational_state": [
            {
                "canonical_key": line.canonical_key,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price) if line.unit_price is not None else None,
                "governing_source_artifact": line.governing_source_artifact,
                "source_artifacts": line.source_artifacts,
                "status": line.status,
            }
            for line in pipeline.reconciled_lines
        ],
        "evidence_chain": {
            "claim": pipeline.evidence.claim,
            "nodes": [
                {
                    "kind": node.kind,
                    "label": node.label,
                    "status": node.status,
                    "evidence": [_evidence_payload(item) for item in node.evidence],
                }
                for node in pipeline.evidence.nodes
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic BOM evidence-backed pipeline.")
    parser.add_argument(
        "--bom",
        type=Path,
        default=_default_bom_path(),
        help="Path to a constrained synthetic XLSX BOM fixture.",
    )
    parser.add_argument(
        "--candidate",
        action="append",
        help="Canonical identifier candidate; repeat to provide multiple candidates.",
    )
    args = parser.parse_args()

    bom = read_bom(args.bom)
    candidates = tuple(args.candidate) if args.candidate else tuple(line.sku for line in bom.lines)
    print(json.dumps(demo_payload(bom, candidates), indent=2))


if __name__ == "__main__":
    main()
