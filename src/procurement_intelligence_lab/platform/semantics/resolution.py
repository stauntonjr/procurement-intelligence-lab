"""Reusable entity-resolution decision contracts."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance


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

    def __post_init__(self) -> None:
        if not self.mention or not self.rationale:
            raise ValueError("resolution mention and rationale are required")
        if self.status is ResolutionStatus.RESOLVED and not self.canonical_key:
            raise ValueError("resolved decisions require a canonical key")
        if self.status is ResolutionStatus.UNRESOLVED and self.canonical_key is not None:
            raise ValueError("unresolved decisions must not carry a canonical key")
