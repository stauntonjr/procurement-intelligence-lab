"""Universal normalized-observation contract."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.documents import MappedField
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.values import (
    SemanticValue,
    validate_semantic_value,
)


@dataclass(frozen=True)
class NormalizedObservation:
    observation_key: str
    subject_hint: str
    predicate: str
    value: SemanticValue | None
    unit: str | None
    source_field: MappedField
    scope: StateScope
    effective_at: datetime
    status: EpistemicStatus
    provenance: DecisionProvenance
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        if not all(
            (self.observation_key.strip(), self.subject_hint.strip(), self.predicate.strip())
        ):
            raise SemanticContractError("observation key, subject hint, and predicate are required")
        if self.unit is not None and not self.unit.strip():
            raise SemanticContractError("unit must be non-empty when present")
        if self.effective_at.tzinfo is None:
            raise TemporalContractError("observation effective_at must be timezone-aware")
        if self.value is None:
            if self.status is not EpistemicStatus.UNRESOLVED or not self.diagnostic:
                raise SemanticContractError(
                    "missing normalized values require unresolved status and a diagnostic"
                )
        else:
            validate_semantic_value(self.value)
            if self.status is EpistemicStatus.UNRESOLVED:
                raise SemanticContractError(
                    "unresolved normalized observations must not carry a value"
                )
        if self.source_field.raw_value is None and self.value is not None:
            raise SemanticContractError("a missing source field cannot yield a resolved value")

    @property
    def observation_id(self) -> str:
        return stable_id(
            "normalized-observation",
            self.observation_key,
            self.subject_hint,
            self.predicate,
            self.value,
            self.unit,
            self.source_field.field_key,
            self.scope,
            self.effective_at.isoformat(),
            self.status.value,
            self.provenance.provenance_id,
        )
