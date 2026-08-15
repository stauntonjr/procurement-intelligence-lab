from decimal import Decimal

import pytest

from procurement_intelligence_lab.application.evidence_service import (
    ClaimKind,
    inspect_bom_claims,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domains.procurement.scope import Permission, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        "reviewer", "tenant", "project", "site", frozenset({Permission.READ_STATE}), "trace"
    )


def _line(sku: str, description: str, quantity: str, row: int) -> BomLine:
    return BomLine(
        sku,
        description,
        Decimal(quantity),
        Decimal(100),
        EvidenceRef("bom.xlsx", "hash", "BOM", row, ("A", "B", "C", "D")),
    )


@pytest.mark.contract
def test_unresolved_identity_cannot_become_an_authoritative_gpu_claim() -> None:
    bom = Bom("bom.xlsx", (_line("GPU-ALIAS", "GPU accelerator", "9", 2),))

    claim = next(
        item
        for item in inspect_bom_claims(bom, ("GPU-A",), request_context=_context())
        if item.kind is ClaimKind.GPU_QUANTITY
    )

    assert claim.value is None
    assert claim.status == "unresolved"
    assert claim.execution_trace.nodes[-1].status == "unresolved"


@pytest.mark.contract
def test_each_claim_trace_contains_only_material_source_evidence() -> None:
    gpu = _line("GPU-A", "GPU accelerator", "4", 2)
    cpu = _line("CPU-A", "CPU", "2", 3)

    claims = {
        claim.kind: claim
        for claim in inspect_bom_claims(
            Bom("bom.xlsx", (gpu, cpu)),
            ("GPU-A", "CPU-A"),
            request_context=_context(),
        )
    }

    gpu_claim = claims[ClaimKind.GPU_QUANTITY]
    cost_claim = claims[ClaimKind.BOM_COST]
    assert gpu_claim.evidence == (gpu.evidence,)
    assert all(node.evidence == (gpu.evidence,) for node in gpu_claim.execution_trace.nodes)
    assert cost_claim.evidence == (gpu.evidence, cpu.evidence)
    assert gpu_claim.execution_trace.chain_id != cost_claim.execution_trace.chain_id


@pytest.mark.contract
def test_missing_price_makes_cost_value_and_trace_unresolved() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B", "C", "D"))
    line = BomLine("GPU-A", "GPU accelerator", Decimal(4), None, evidence)

    claim = next(
        item
        for item in inspect_bom_claims(
            Bom("bom.xlsx", (line,)),
            ("GPU-A",),
            request_context=_context(),
        )
        if item.kind is ClaimKind.BOM_COST
    )

    assert claim.value is None
    assert claim.status == "unresolved"
    assert claim.execution_trace.nodes[-1].status == "unresolved"


@pytest.mark.contract
def test_empty_inputs_never_emit_authoritative_zero_or_empty_values() -> None:
    claims = inspect_bom_claims(Bom("bom.xlsx", ()), (), request_context=_context())

    assert all(claim.value is None for claim in claims)
    assert all(claim.status == "unresolved" for claim in claims)
    assert all(claim.execution_trace.nodes[-1].status == "unresolved" for claim in claims)
