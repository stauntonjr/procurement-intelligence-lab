from decimal import Decimal

from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    local_provenance_context,
)
from procurement_intelligence_lab.domain.reconciliation import (
    ReconciliationPolicy,
    reconcile_lines,
)
from procurement_intelligence_lab.domain.state import OperationalBomLine


def test_reconciliation_selects_governing_claim_and_retains_conflicts() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    lines = (
        OperationalBomLine("gpu", Decimal(4), Decimal(100), "bom-a.xlsx", evidence),
        OperationalBomLine("gpu", Decimal(2), Decimal(100), "bom-b.xlsx", evidence),
        OperationalBomLine("cpu", Decimal(1), Decimal(20), "bom-a.xlsx", evidence),
        OperationalBomLine("cpu", Decimal(1), Decimal(25), "bom-b.xlsx", evidence),
    )
    provenance = DecisionProvenance(
        local_provenance_context(),
        "test-reconciliation",
        ComponentKind.DETERMINISTIC,
        "1",
    )

    result = reconcile_lines(
        lines,
        policy=ReconciliationPolicy(("bom-a.xlsx", "bom-b.xlsx")),
        provenance=provenance,
    )

    assert result[0].canonical_key == "cpu"
    assert result[0].unit_price == Decimal(20)
    assert result[0].governing_source_artifact == "bom-a.xlsx"
    assert result[0].status == "conflict"
    assert result[0].provenance.provenance_id == provenance.provenance_id
    assert result[1].canonical_key == "gpu"
    assert result[1].quantity == Decimal(4)
    assert result[1].status == "conflict"
