"""Evidence-backed anomaly types and deterministic comparison helpers."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.identity import stable_id
from procurement_intelligence_lab.domain.provenance import DecisionProvenance


class AnomalyKind(StrEnum):
    MISSING_PO = "missing_po"
    QUANTITY_MISMATCH = "quantity_mismatch"
    STALE_REVISION = "stale_revision"
    SUBSTITUTION = "substitution"
    LATE_COMMITMENT = "late_commitment"
    PRICE_DEVIATION = "price_deviation"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    COVERAGE_GAP = "coverage_gap"


class AnomalySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AnomalyStatus(StrEnum):
    OPEN = "open"
    SUPPRESSED = "suppressed"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class AnomalyPolicy:
    """Auditable tolerances for deterministic anomaly comparisons."""

    policy_id: str
    quantity_tolerance: Decimal = Decimal(0)
    price_tolerance: Decimal = Decimal(0)
    late_days_tolerance: int = 0

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id must not be empty")
        if self.quantity_tolerance < 0 or self.price_tolerance < 0:
            raise ValueError("numeric tolerances must be non-negative")
        if self.late_days_tolerance < 0:
            raise ValueError("late_days_tolerance must be non-negative")


@dataclass(frozen=True)
class Anomaly:
    """A typed deviation retaining evidence and decision provenance."""

    subject_key: str
    kind: AnomalyKind
    expected: object | None
    observed: object | None
    severity: AnomalySeverity
    status: AnomalyStatus
    evidence: tuple[EvidenceRef, ...]
    policy_id: str
    provenance: DecisionProvenance
    detected_at: datetime

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id must not be empty")
        if self.detected_at.tzinfo is None:
            raise ValueError("detected_at must be timezone-aware")

    @property
    def anomaly_id(self) -> str:
        return stable_id(
            "anomaly",
            self.subject_key,
            self.kind.value,
            str(self.expected),
            str(self.observed),
            tuple(sorted(ref.evidence_id for ref in self.evidence)),
            self.policy_id,
            self.provenance.provenance_id,
        )


def detect_quantity_mismatch(
    subject_key: str,
    expected: Decimal,
    observed: Decimal,
    evidence: tuple[EvidenceRef, ...],
    *,
    policy: AnomalyPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    if abs(observed - expected) <= policy.quantity_tolerance:
        return None
    return Anomaly(
        subject_key,
        AnomalyKind.QUANTITY_MISMATCH,
        expected,
        observed,
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )


def detect_price_deviation(
    subject_key: str,
    expected: Decimal,
    observed: Decimal,
    evidence: tuple[EvidenceRef, ...],
    *,
    policy: AnomalyPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    if abs(observed - expected) <= policy.price_tolerance:
        return None
    return Anomaly(
        subject_key,
        AnomalyKind.PRICE_DEVIATION,
        expected,
        observed,
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )


def detect_late_commitment(
    subject_key: str,
    expected: date,
    observed: date,
    evidence: tuple[EvidenceRef, ...],
    *,
    policy: AnomalyPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    if observed <= expected + timedelta(days=policy.late_days_tolerance):
        return None
    return Anomaly(
        subject_key,
        AnomalyKind.LATE_COMMITMENT,
        expected,
        observed,
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )
