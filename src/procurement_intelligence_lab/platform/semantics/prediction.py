"""Universal scoped prediction contracts with explicit uncertainty."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from procurement_intelligence_lab.platform.semantics.errors import (
    ScopeMismatchError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.state import OperationalState
from procurement_intelligence_lab.platform.semantics.values import (
    SemanticValue,
    validate_semantic_value,
)


@dataclass(frozen=True)
class EvidenceAndState:
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    states: tuple[OperationalState, ...]

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise TemporalContractError("prediction input as_of must be timezone-aware")
        if not self.evidence and not self.states:
            raise SemanticContractError("prediction input requires evidence or operational state")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("prediction input evidence must be unique")
        if len({item.state_id for item in self.states}) != len(self.states):
            raise SemanticContractError("prediction input states must be unique")
        for state in self.states:
            if state.scope != self.scope:
                raise ScopeMismatchError("prediction input states must share one scope")
            if state.as_of > self.as_of:
                raise TemporalContractError(
                    "prediction input cannot include future operational state"
                )

    @property
    def input_id(self) -> str:
        return stable_id(
            "prediction-input",
            self.scope,
            self.as_of.isoformat(),
            tuple(item.evidence_id for item in self.evidence),
            tuple(item.state_id for item in self.states),
        )


@dataclass(frozen=True)
class Prediction:
    subject_key: str
    outcome: str
    predicted_value: SemanticValue
    confidence: Decimal
    uncertainty_basis: str
    scope: StateScope
    as_of: datetime
    horizon_start: datetime
    horizon_end: datetime
    evidence: tuple[EvidenceRef, ...]
    inputs: EvidenceAndState
    provenance: DecisionProvenance
    unit: str | None = None

    def __post_init__(self) -> None:
        if not self.subject_key.strip() or not self.outcome.strip():
            raise SemanticContractError("prediction subject and outcome are required")
        validate_semantic_value(self.predicted_value)
        if (
            not self.confidence.is_finite()
            or self.confidence < Decimal(0)
            or self.confidence > Decimal(1)
        ):
            raise SemanticContractError("prediction confidence must be in [0, 1]")
        if not self.uncertainty_basis.strip():
            raise SemanticContractError("prediction uncertainty basis is required")
        if any(item.tzinfo is None for item in (self.as_of, self.horizon_start, self.horizon_end)):
            raise TemporalContractError("prediction timestamps must be timezone-aware")
        if not self.as_of <= self.horizon_start <= self.horizon_end:
            raise TemporalContractError(
                "prediction horizon must begin at or after as_of and end after it begins"
            )
        if not self.evidence:
            raise SemanticContractError("predictions require evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("prediction evidence must be unique")
        if self.inputs.scope != self.scope:
            raise ScopeMismatchError("prediction and inputs must share one scope")
        if self.inputs.as_of > self.as_of:
            raise TemporalContractError("prediction cannot precede its input as_of")
        available_evidence = {item.evidence_id for item in self.inputs.evidence}
        available_evidence.update(
            item.evidence_id for state in self.inputs.states for item in state.evidence
        )
        if any(item.evidence_id not in available_evidence for item in self.evidence):
            raise SemanticContractError(
                "prediction evidence must originate in its evidence/state input"
            )
        if self.unit is not None and not self.unit.strip():
            raise SemanticContractError("prediction unit must be non-empty when present")

    @property
    def input_id(self) -> str:
        return self.inputs.input_id

    @property
    def prediction_id(self) -> str:
        return stable_id(
            "prediction",
            self.subject_key,
            self.outcome,
            self.predicted_value,
            self.confidence,
            self.uncertainty_basis,
            self.scope,
            self.as_of.isoformat(),
            self.horizon_start.isoformat(),
            self.horizon_end.isoformat(),
            tuple(item.evidence_id for item in self.evidence),
            self.inputs.input_id,
            self.provenance.provenance_id,
            self.unit,
        )
