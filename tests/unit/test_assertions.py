from decimal import Decimal

from procurement_intelligence_lab.domain.assertions import (
    AssertionPredicate,
    assertions_for_bom_line,
)
from procurement_intelligence_lab.domain.bom import EvidenceRef


def test_assertions_preserve_source_evidence_and_omit_missing_values() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A", "B", "C", "D"))
    assertions = assertions_for_bom_line("GPU-A", "GPU accelerator", Decimal(4), None, evidence)

    assert [item.predicate for item in assertions] == [
        AssertionPredicate.HAS_SKU,
        AssertionPredicate.HAS_DESCRIPTION,
        AssertionPredicate.HAS_QUANTITY,
    ]
    assert all(item.evidence == evidence for item in assertions)
