"""Reusable entity-mention, resolution, and canonicalization contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class EntityMention:
    """A source-grounded entity surface form awaiting resolution."""

    text: str
    entity_type: str
    assertions: tuple[SourceAssertion, ...]
    scope: StateScope
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.text.strip() or not self.entity_type.strip():
            raise SemanticContractError("entity mention text and type are required")
        if not self.assertions:
            raise SemanticContractError("entity mentions require source assertions")
        if self.observed_at.tzinfo is None:
            raise TemporalContractError("entity mention observed_at must be timezone-aware")

    @property
    def mention_id(self) -> str:
        return stable_id(
            "entity-mention",
            self.text,
            self.entity_type,
            tuple(item.assertion_id for item in self.assertions),
            self.scope,
            self.observed_at.isoformat(),
        )


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

    @property
    def decision_id(self) -> str:
        return stable_id(
            "resolution-decision",
            self.mention,
            self.canonical_key,
            self.status.value,
            tuple(item.assertion_id for item in self.evidence),
            self.rationale,
            self.provenance.provenance_id,
        )


@dataclass(frozen=True)
class CanonicalizedAssertion:
    """A source assertion linked to an explicit successful identity decision."""

    assertion: SourceAssertion
    resolution: ResolutionDecision
    scope: StateScope
    effective_at: datetime

    def __post_init__(self) -> None:
        if self.resolution.status is not ResolutionStatus.RESOLVED:
            raise SemanticContractError(
                "canonicalized assertions require a resolved identity decision"
            )
        if self.resolution.canonical_key is None:
            raise SemanticContractError("canonicalized assertions require a canonical key")
        resolved_subjects = {item.subject_key for item in self.resolution.evidence}
        if self.assertion.subject_key not in resolved_subjects:
            raise SemanticContractError(
                "canonicalized assertion must share a subject with resolution evidence"
            )
        if self.effective_at.tzinfo is None:
            raise TemporalContractError(
                "canonicalized assertion effective_at must be timezone-aware"
            )

    @property
    def canonical_key(self) -> str:
        assert self.resolution.canonical_key is not None
        return self.resolution.canonical_key

    @property
    def canonicalized_assertion_id(self) -> str:
        return stable_id(
            "canonicalized-assertion",
            self.assertion.assertion_id,
            self.resolution.decision_id,
            self.scope,
            self.effective_at.isoformat(),
        )
