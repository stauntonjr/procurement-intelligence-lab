from procurement_intelligence_lab.domain.assertions import (
    AssertionPredicate,
    SourceAssertion,
)
from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.resolution import (
    ResolutionStatus,
    normalize_identifier,
    resolve_identifier,
)


def test_normalized_exact_match_is_resolved() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    assertion = SourceAssertion("GPU-A", AssertionPredicate.HAS_SKU, "GPU-A", evidence)

    decision = resolve_identifier("gpu a", ("GPU-A", "CPU-A"), (assertion,))

    assert normalize_identifier("GPU-A") == "gpua"
    assert decision.canonical_key == "GPU-A"
    assert decision.status is ResolutionStatus.RESOLVED
    assert decision.evidence == (assertion,)


def test_ambiguous_or_missing_match_stays_unresolved() -> None:
    ambiguous = resolve_identifier("gpu a", ("GPU-A", "GPU A"))
    missing = resolve_identifier("unknown", ("GPU-A",))

    assert ambiguous.status is ResolutionStatus.UNRESOLVED
    assert "ambiguous" in ambiguous.rationale
    assert missing.status is ResolutionStatus.UNRESOLVED
    assert missing.evidence == ()
