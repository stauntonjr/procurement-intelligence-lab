"""Conservative entity-resolution decisions over source assertions."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.domain.assertions import AssertionPredicate, SourceAssertion
from procurement_intelligence_lab.domain.provenance import DecisionProvenance


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ResolutionDecision:
    mention: str
    canonical_key: str | None
    status: ResolutionStatus
    evidence: tuple[SourceAssertion, ...]
    rationale: str
    provenance: DecisionProvenance


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
        and assertion.predicate is AssertionPredicate.HAS_SKU
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
