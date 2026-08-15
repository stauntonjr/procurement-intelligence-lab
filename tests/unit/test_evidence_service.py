from decimal import Decimal

from procurement_intelligence_lab.application.evidence_service import (
    ClaimKind,
    inspect_bom_claims,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domains.procurement.scope import Permission, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        "user", "tenant", "project", "site", frozenset({Permission.READ_STATE}), "trace"
    )


def test_claim_service_exposes_deterministic_values_and_execution_trace() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B", "C", "D"))
    bom = Bom(
        "bom.xlsx",
        (
            BomLine("GPU-A", "GPU accelerator", Decimal(4), Decimal(100), evidence),
            BomLine("CPU-A", "CPU", Decimal(2), Decimal(50), evidence),
        ),
    )

    claims = inspect_bom_claims(bom, ("GPU-A", "CPU-A"), request_context=_context())

    assert [claim.kind for claim in claims] == [
        ClaimKind.DISTINCT_SKUS,
        ClaimKind.GPU_QUANTITY,
        ClaimKind.BOM_COST,
    ]
    assert claims[-1].value == Decimal(500)
    assert claims[-1].evidence == (evidence, evidence)
    assert [node.label for node in claims[-1].execution_trace.nodes] == [
        "source assertions",
        "entity resolution",
        "operational state",
        "reconciliation",
    ]
