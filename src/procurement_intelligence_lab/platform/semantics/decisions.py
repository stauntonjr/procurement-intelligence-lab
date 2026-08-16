"""Universal evidence bundle, authority, and decision contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly
from procurement_intelligence_lab.platform.semantics.derivation import DerivedFact
from procurement_intelligence_lab.platform.semantics.errors import (
    AuthorityContractError,
    ScopeMismatchError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.prediction import Prediction
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class FactsAnomaliesPredictions:
    scope: StateScope
    as_of: datetime
    facts: tuple[DerivedFact, ...] = ()
    anomalies: tuple[Anomaly, ...] = ()
    predictions: tuple[Prediction, ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise TemporalContractError("decision input as_of must be timezone-aware")
        if not (self.facts or self.anomalies or self.predictions):
            raise SemanticContractError("decision input requires facts, anomalies, or predictions")
        identities = (
            tuple(item.fact_id for item in self.facts),
            tuple(item.anomaly_id for item in self.anomalies),
            tuple(item.prediction_id for item in self.predictions),
        )
        if any(len(items) != len(set(items)) for items in identities):
            raise SemanticContractError("decision inputs must not contain duplicates")
        if any(item.scope != self.scope for item in self.facts):
            raise ScopeMismatchError("decision facts must share the input scope")
        if any(item.scope != self.scope for item in self.predictions):
            raise ScopeMismatchError("decision predictions must share the input scope")
        if any(item.scope != self.scope for item in self.anomalies):
            raise ScopeMismatchError("decision anomalies require an explicit matching scope")
        if any(item.as_of > self.as_of for item in self.facts):
            raise TemporalContractError("decision input cannot include future facts")
        if any(item.as_of > self.as_of for item in self.predictions):
            raise TemporalContractError("decision input cannot include future predictions")
        if any(item.detected_at > self.as_of for item in self.anomalies):
            raise TemporalContractError("decision input cannot include future anomalies")

    @property
    def input_id(self) -> str:
        return stable_id(
            "decision-input",
            self.scope,
            self.as_of.isoformat(),
            tuple(item.fact_id for item in self.facts),
            tuple(item.anomaly_id for item in self.anomalies),
            tuple(item.prediction_id for item in self.predictions),
        )


@dataclass(frozen=True)
class DecisionAuthority:
    authority_id: str
    principal_id: str
    role: str
    scope: StateScope
    may_approve_actions: bool = False

    def __post_init__(self) -> None:
        if not all((self.authority_id.strip(), self.principal_id.strip(), self.role.strip())):
            raise AuthorityContractError("decision authority ID, principal, and role are required")


class DecisionOutcome(StrEnum):
    RECOMMEND = "recommend"
    DEFER = "defer"
    REJECT = "reject"


@dataclass(frozen=True)
class Decision:
    subject_key: str
    outcome: DecisionOutcome
    rationale: str
    policy_id: str
    authority: DecisionAuthority
    inputs: FactsAnomaliesPredictions
    evidence: tuple[EvidenceRef, ...]
    decided_at: datetime
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if not all((self.subject_key.strip(), self.rationale.strip(), self.policy_id.strip())):
            raise SemanticContractError("decision subject, rationale, and policy ID are required")
        if self.authority.scope != self.inputs.scope:
            raise ScopeMismatchError("decision authority and inputs must share one scope")
        if self.decided_at.tzinfo is None:
            raise TemporalContractError("decision decided_at must be timezone-aware")
        if self.decided_at < self.inputs.as_of:
            raise TemporalContractError("decision cannot precede its input as_of")
        if not self.evidence:
            raise SemanticContractError("decisions require evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("decision evidence must be unique")

    @property
    def decision_id(self) -> str:
        return stable_id(
            "decision",
            self.subject_key,
            self.outcome.value,
            self.rationale,
            self.policy_id,
            self.authority.authority_id,
            self.inputs.input_id,
            tuple(item.evidence_id for item in self.evidence),
            self.decided_at.isoformat(),
            self.provenance.provenance_id,
        )
