from decimal import Decimal

from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    local_provenance_context,
)
from procurement_intelligence_lab.domain.reconciliation import reconcile_lines
from procurement_intelligence_lab.domain.state import OperationalBomLine


def test_reconciliation_aggregates_and_exposes_price_conflicts() -> None:
    lines = (
        OperationalBomLine("gpu", Decimal(4), Decimal(100), "bom-a.xlsx"),
        OperationalBomLine("gpu", Decimal(2), Decimal(100), "bom-b.xlsx"),
        OperationalBomLine("cpu", Decimal(1), Decimal(20), "bom-a.xlsx"),
        OperationalBomLine("cpu", Decimal(1), Decimal(25), "bom-b.xlsx"),
    )
    provenance = DecisionProvenance(
        local_provenance_context(),
        "test-reconciliation",
        ComponentKind.DETERMINISTIC,
        "1",
    )

    result = reconcile_lines(lines, provenance=provenance)

    assert result[0].canonical_key == "cpu"
    assert result[0].unit_price is None
    assert result[0].status == "conflict"
    assert result[0].provenance.provenance_id == provenance.provenance_id
    assert result[1].canonical_key == "gpu"
    assert result[1].quantity == Decimal(6)
    assert result[1].status == "reconciled"
