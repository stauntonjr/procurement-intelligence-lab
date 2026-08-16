"""Universal deterministic derived-fact contract."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.values import (
    SemanticValue,
    validate_semantic_value,
)


@dataclass(frozen=True)
class DerivedFact:
    subject_key: str
    predicate: str
    value: SemanticValue
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    source_state_ids: tuple[str, ...]
    provenance: DecisionProvenance
    status: EpistemicStatus = EpistemicStatus.INFERRED
    unit: str | None = None

    def __post_init__(self) -> None:
        if not self.subject_key.strip() or not self.predicate.strip():
            raise SemanticContractError("derived fact subject and predicate are required")
        validate_semantic_value(self.value)
        if self.as_of.tzinfo is None:
            raise TemporalContractError("derived fact as_of must be timezone-aware")
        if not self.evidence or not self.source_state_ids:
            raise SemanticContractError(
                "derived facts require evidence and source operational-state IDs"
            )
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("derived-fact evidence must be unique")
        if any(not item.strip() for item in self.source_state_ids):
            raise SemanticContractError("source operational-state IDs must be non-empty")
        if len(set(self.source_state_ids)) != len(self.source_state_ids):
            raise SemanticContractError("source operational-state IDs must be unique")
        if self.status is not EpistemicStatus.INFERRED:
            raise SemanticContractError("derived facts must have inferred epistemic status")
        if self.unit is not None and not self.unit.strip():
            raise SemanticContractError("derived fact unit must be non-empty when present")

    @property
    def fact_id(self) -> str:
        return stable_id(
            "derived-fact",
            self.subject_key,
            self.predicate,
            self.value,
            self.scope,
            self.as_of.isoformat(),
            tuple(item.evidence_id for item in self.evidence),
            self.source_state_ids,
            self.provenance.provenance_id,
            self.unit,
        )
