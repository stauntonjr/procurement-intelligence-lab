"""Conservative entity-resolution decisions over source assertions."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.domain.assertions import AssertionPredicate, SourceAssertion


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


def normalize_identifier(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def resolve_identifier(
    mention: str,
    candidates: tuple[str, ...],
    assertions: tuple[SourceAssertion, ...] = (),
) -> ResolutionDecision:
    normalized = normalize_identifier(mention)
    matches = tuple(
        candidate for candidate in candidates if normalize_identifier(candidate) == normalized
    )
    if len(matches) == 1:
        return ResolutionDecision(
            mention,
            matches[0],
            ResolutionStatus.RESOLVED,
            tuple(
                assertion
                for assertion in assertions
                if assertion.predicate is AssertionPredicate.HAS_SKU
            ),
            "normalized exact identifier match",
        )
    rationale = "no normalized candidate match" if not matches else "ambiguous normalized candidate match"
    return ResolutionDecision(mention, None, ResolutionStatus.UNRESOLVED, assertions, rationale)
