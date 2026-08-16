"""Reusable anomaly envelope and detector contract."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, cast

from procurement_intelligence_lab.platform.semantics.errors import ScopeMismatchError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class AnomalySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AnomalyStatus(StrEnum):
    OPEN = "open"
    SUPPRESSED = "suppressed"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


class AnomalyDetails(Protocol):
    @property
    def kind(self) -> StrEnum: ...

    @property
    def expected(self) -> object | None: ...

    @property
    def observed(self) -> object | None: ...


@dataclass(frozen=True)
class Anomaly:
    """Evidence/provenance envelope around domain-owned typed anomaly details."""

    subject_key: str
    details: AnomalyDetails
    severity: AnomalySeverity
    status: AnomalyStatus
    evidence: tuple[EvidenceRef, ...]
    policy_id: str
    provenance: DecisionProvenance
    detected_at: datetime
    scope: StateScope

    def __post_init__(self) -> None:
        if not self.subject_key or not self.policy_id:
            raise ValueError("anomaly subject and policy ID are required")
        if not self.evidence:
            raise ValueError("anomalies require evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("anomaly evidence must be unique")
        if self.detected_at.tzinfo is None:
            raise ValueError("detected_at must be timezone-aware")
        scope_value = cast(object, self.scope)
        if not isinstance(scope_value, StateScope):
            raise ScopeMismatchError("anomalies require an explicit state scope")

    @property
    def kind(self) -> StrEnum:
        return self.details.kind

    @property
    def expected(self) -> object | None:
        return self.details.expected

    @property
    def observed(self) -> object | None:
        return self.details.observed

    @property
    def anomaly_id(self) -> str:
        # Preserve the established identity contract while replacing untyped payload fields.
        return stable_id(
            "anomaly",
            self.subject_key,
            self.scope,
            self.kind.value,
            str(self.expected),
            str(self.observed),
            tuple(sorted(ref.evidence_id for ref in self.evidence)),
            self.policy_id,
            self.provenance.provenance_id,
        )


class Detector(Protocol):
    """Runtime detector contract; DomainPackage data stores only its versioned reference."""

    def detect(self, subject: object, *, detected_at: datetime) -> tuple[Anomaly, ...]: ...
