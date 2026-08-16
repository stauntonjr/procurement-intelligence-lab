"""Conservative entity-resolution decisions over source assertions."""

from procurement_intelligence_lab.domains.procurement.assertions import (
    AssertionPredicate,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)


def normalize_identifier(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def resolve_identifier(
    mention: str,
    candidates: tuple[str, ...],
    assertions: tuple[SourceAssertion, ...] = (),
    *,
    provenance: DecisionProvenance,
) -> ResolutionDecision:
    normalized = normalize_identifier(mention)
    matches = tuple(
        candidate for candidate in candidates if normalize_identifier(candidate) == normalized
    )
    relevant_assertions = tuple(
        assertion
        for assertion in assertions
        if normalize_identifier(assertion.subject_key) == normalized
        and assertion.predicate.value == AssertionPredicate.HAS_SKU.value
    )
    if len(matches) == 1:
        return ResolutionDecision(
            mention,
            matches[0],
            ResolutionStatus.RESOLVED,
            relevant_assertions,
            "normalized exact identifier match",
            provenance,
        )
    rationale = (
        "no normalized candidate match" if not matches else "ambiguous normalized candidate match"
    )
    return ResolutionDecision(
        mention,
        None,
        ResolutionStatus.UNRESOLVED,
        relevant_assertions,
        rationale,
        provenance,
    )
