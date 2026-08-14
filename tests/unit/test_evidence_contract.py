from decimal import Decimal

from procurement_intelligence_lab.application.pipeline import run_bom_pipeline
from procurement_intelligence_lab.domain.bom import (
    Bom,
    BomLine,
    EpistemicStatus,
    EvidenceRef,
    bom_cost,
)
from procurement_intelligence_lab.domain.evidence import EvidenceNodeKind
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    local_provenance_context,
)
from procurement_intelligence_lab.domain.reconciliation import reconcile_lines
from procurement_intelligence_lab.domain.state import OperationalBomLine


def line(sku: str, quantity: str, price: str | None, row: int) -> BomLine:
    return BomLine(
        sku,
        "GPU accelerator" if sku.startswith("GPU") else "CPU",
        Decimal(quantity),
        Decimal(price) if price is not None else None,
        EvidenceRef("synthetic_bom.xlsx", "fixture-hash", "BOM", row, ("A", "B", "C", "D")),
    )


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        local_provenance_context(),
        "test-reconciliation",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def test_resolved_claim_preserves_complete_evidence_contract() -> None:
    bom = Bom("synthetic_bom.xlsx", (line("GPU-A", "4", "100", 2), line("CPU-A", "2", "50", 3)))

    result = run_bom_pipeline(bom, ("GPU-A", "CPU-A"))

    assert bom_cost(bom).value == Decimal(500)
    assert bom_cost(bom).status is EpistemicStatus.OBSERVED
    assert [node.kind for node in result.evidence.nodes] == [
        EvidenceNodeKind.SOURCE_ASSERTION,
        EvidenceNodeKind.RESOLUTION,
        EvidenceNodeKind.OPERATIONAL_STATE,
        EvidenceNodeKind.RECONCILIATION,
    ]
    assert all(
        node.evidence == tuple(item.evidence for item in bom.lines)
        for node in result.evidence.nodes
    )
    assert {ref.sheet for ref in result.evidence.nodes[0].evidence} == {"BOM"}
    assert {ref.row for ref in result.evidence.nodes[0].evidence} == {2, 3}
    assert all(ref.cells == ("A", "B", "C", "D") for ref in result.evidence.nodes[0].evidence)


def test_incomplete_price_and_unresolved_identity_abstain_from_canonical_state() -> None:
    bom = Bom("synthetic_bom.xlsx", (line("UNKNOWN", "4", None, 2),))

    result = run_bom_pipeline(bom, ("GPU-A",))

    assert bom_cost(bom).value is None
    assert bom_cost(bom).status is EpistemicStatus.UNRESOLVED
    assert result.reconciled_lines == ()
    assert result.evidence.nodes[1].status == "partially_resolved"
    assert result.evidence.nodes[2].status == "unresolved"


def test_conflicting_prices_retain_both_artifacts() -> None:
    reconciled = reconcile_lines(
        (
            OperationalBomLine("GPU-A", Decimal(1), Decimal(100), "bom-a.xlsx", line("GPU-A", "1", "100", 2).evidence),
            OperationalBomLine("GPU-A", Decimal(1), Decimal(125), "bom-b.xlsx", line("GPU-A", "1", "125", 3).evidence),
        ),
        provenance=_provenance(),
    )

    assert reconciled[0].status == "conflict"
    assert reconciled[0].unit_price is None
    assert reconciled[0].source_artifacts == ("bom-a.xlsx", "bom-b.xlsx")
