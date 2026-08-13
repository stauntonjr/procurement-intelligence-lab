from decimal import Decimal
from procurement_intelligence_lab.domain.bom import Bom, BomLine, EvidenceRef, EpistemicStatus, bom_cost, distinct_skus, gpu_quantity

def line(sku, description, quantity, price):
    return BomLine(sku, description, Decimal(quantity), Decimal(price) if price else None, EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A","B","C","D")))

def test_deterministic_queries_preserve_evidence():
    bom = Bom("fixture.xlsx", (line("GPU-A", "GPU accelerator", "4", "100"), line("CPU-A", "CPU", "2", "50")))
    assert distinct_skus(bom).value == ("CPU-A", "GPU-A")
    assert gpu_quantity(bom).value == Decimal("4")
    result = bom_cost(bom)
    assert result.value == Decimal("500")
    assert result.status is EpistemicStatus.OBSERVED
    assert len(result.evidence) == 2

def test_missing_price_abstains_from_cost():
    result = bom_cost(Bom("fixture.xlsx", (line("GPU-A", "GPU", "1", None),)))
    assert result.value is None
    assert result.status is EpistemicStatus.UNRESOLVED
