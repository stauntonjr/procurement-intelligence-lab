from procurement_intelligence_lab.domains.procurement.assertions import (
    AssertionPredicate,
    SourceAssertion,
)
from procurement_intelligence_lab.domains.procurement.bom import EvidenceRef
from procurement_intelligence_lab.domains.procurement.provenance import (
    ComponentKind,
    DecisionProvenance,
    local_provenance_context,
)
from procurement_intelligence_lab.domains.procurement.resolution import (
    ResolutionStatus,
    normalize_identifier,
    resolve_identifier,
)


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        local_provenance_context(),
        "test-resolver",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def test_normalized_exact_match_is_resolved() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    assertion = SourceAssertion("GPU-A", AssertionPredicate.HAS_SKU, "GPU-A", evidence)

    decision = resolve_identifier(
        "gpu a",
        ("GPU-A", "CPU-A"),
        (assertion,),
        provenance=_provenance(),
    )

    assert normalize_identifier("GPU-A") == "gpua"
    assert decision.canonical_key == "GPU-A"
    assert decision.status is ResolutionStatus.RESOLVED
    assert decision.evidence == (assertion,)
    assert decision.provenance.component_name == "test-resolver"


def test_ambiguous_or_missing_match_stays_unresolved() -> None:
    ambiguous = resolve_identifier(
        "gpu a",
        ("GPU-A", "GPU A"),
        provenance=_provenance(),
    )
    missing = resolve_identifier(
        "unknown",
        ("GPU-A",),
        provenance=_provenance(),
    )

    assert ambiguous.status is ResolutionStatus.UNRESOLVED
    assert "ambiguous" in ambiguous.rationale
    assert missing.status is ResolutionStatus.UNRESOLVED
    assert missing.evidence == ()
