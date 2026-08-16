"""Shared governed operational-state contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

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


class StateFreshness(StrEnum):
    CURRENT = "current"
    PARTIAL = "partial"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StateAttribute:
    name: str
    value: SemanticValue | None
    status: EpistemicStatus
    evidence: tuple[EvidenceRef, ...]
    unit: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise SemanticContractError("state attribute name is required")
        if self.unit is not None and not self.unit.strip():
            raise SemanticContractError("state attribute unit must be non-empty when present")
        if self.value is None:
            if self.status is not EpistemicStatus.UNRESOLVED:
                raise SemanticContractError("missing state values must be unresolved")
        else:
            validate_semantic_value(self.value)
            if self.status is EpistemicStatus.UNRESOLVED:
                raise SemanticContractError("unresolved state attributes cannot carry a value")
        if not self.evidence:
            raise SemanticContractError("state attributes require evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("state attribute evidence must be unique")


@dataclass(frozen=True)
class OperationalState:
    subject_key: str
    scope: StateScope
    as_of: datetime
    freshness: StateFreshness
    attributes: tuple[StateAttribute, ...]
    evidence: tuple[EvidenceRef, ...]
    provenance: DecisionProvenance
    reconciliation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.subject_key.strip():
            raise SemanticContractError("operational-state subject is required")
        if self.as_of.tzinfo is None:
            raise TemporalContractError("operational-state as_of must be timezone-aware")
        if not self.attributes:
            raise SemanticContractError("operational state requires at least one attribute")
        attribute_names = tuple(item.name for item in self.attributes)
        if len(attribute_names) != len(set(attribute_names)):
            raise SemanticContractError("operational-state attribute names must be unique")
        if not self.evidence:
            raise SemanticContractError("operational state requires evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("operational-state evidence must be unique")
        state_evidence = {item.evidence_id for item in self.evidence}
        if any(
            ref.evidence_id not in state_evidence
            for attribute in self.attributes
            for ref in attribute.evidence
        ):
            raise SemanticContractError(
                "operational-state evidence must include every attribute evidence reference"
            )
        if self.reconciliation_id is not None and not self.reconciliation_id.strip():
            raise SemanticContractError("reconciliation_id must be non-empty when present")

    @property
    def state_id(self) -> str:
        return stable_id(
            "operational-state",
            self.subject_key,
            self.scope,
            self.as_of.isoformat(),
            self.freshness.value,
            tuple((item.name, item.value, item.status.value) for item in self.attributes),
            tuple(item.evidence_id for item in self.evidence),
            self.provenance.provenance_id,
            self.reconciliation_id,
        )
