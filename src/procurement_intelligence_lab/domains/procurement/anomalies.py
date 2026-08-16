"""Typed procurement anomalies and deterministic per-kind policies."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.domains.procurement.state import ExpectedObservedState
from procurement_intelligence_lab.platform.semantics.anomalies import (
    Anomaly,
    AnomalyDetails,
    AnomalySeverity,
    AnomalyStatus,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.state import StateFreshness


class AnomalyKind(StrEnum):
    MISSING_PO = "missing_po"
    QUANTITY_MISMATCH = "quantity_mismatch"
    STALE_REVISION = "stale_revision"
    SUBSTITUTION = "substitution"
    LATE_COMMITMENT = "late_commitment"
    PRICE_DEVIATION = "price_deviation"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    COVERAGE_GAP = "coverage_gap"


def _validate_policy_id(policy_id: str) -> None:
    if not policy_id.strip():
        raise ValueError("policy_id must not be empty")


def _validate_tolerance(name: str, tolerance: Decimal) -> None:
    if not tolerance.is_finite() or tolerance < Decimal(0):
        raise ValueError(f"{name} must be finite and non-negative")


def _validate_comparison(name: str, value: Decimal) -> None:
    if not value.is_finite() or value < Decimal(0):
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class MissingPurchaseOrderPolicy:
    policy_id: str
    minimum_required_quantity: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        _validate_tolerance("minimum_required_quantity", self.minimum_required_quantity)


@dataclass(frozen=True)
class QuantityMismatchPolicy:
    policy_id: str
    tolerance: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        _validate_tolerance("quantity tolerance", self.tolerance)


@dataclass(frozen=True)
class SubstitutionPolicy:
    policy_id: str
    tolerance: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        _validate_tolerance("substitution tolerance", self.tolerance)


@dataclass(frozen=True)
class CoverageGapPolicy:
    policy_id: str
    unknown_quantity_tolerance: Decimal = Decimal(0)
    flag_non_current: bool = True

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        _validate_tolerance("unknown quantity tolerance", self.unknown_quantity_tolerance)


@dataclass(frozen=True)
class PriceDeviationPolicy:
    policy_id: str
    tolerance: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        _validate_tolerance("price tolerance", self.tolerance)


@dataclass(frozen=True)
class LateCommitmentPolicy:
    policy_id: str
    tolerance: timedelta = timedelta(0)

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)
        if self.tolerance < timedelta(0):
            raise ValueError("late commitment tolerance must be non-negative")


@dataclass(frozen=True)
class StaleRevisionPolicy:
    policy_id: str

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)


@dataclass(frozen=True)
class UnresolvedIdentityPolicy:
    policy_id: str

    def __post_init__(self) -> None:
        _validate_policy_id(self.policy_id)


@dataclass(frozen=True)
class ExpectedObservedAnomalyPolicies:
    missing_purchase_order: MissingPurchaseOrderPolicy
    quantity_mismatch: QuantityMismatchPolicy
    substitution: SubstitutionPolicy
    coverage_gap: CoverageGapPolicy


@dataclass(frozen=True)
class MissingPurchaseOrderDetails:
    expected: Decimal
    observed: Decimal | None

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.MISSING_PO


@dataclass(frozen=True)
class QuantityMismatchDetails:
    expected: Decimal
    observed: Decimal

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.QUANTITY_MISMATCH


@dataclass(frozen=True)
class SubstitutionDetails:
    expected: Decimal
    observed: Decimal

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.SUBSTITUTION


@dataclass(frozen=True)
class CoverageGapDetails:
    expected: Decimal
    observed: Decimal

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.COVERAGE_GAP


@dataclass(frozen=True)
class PriceDeviationDetails:
    expected: Decimal
    observed: Decimal

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.PRICE_DEVIATION


@dataclass(frozen=True)
class LateCommitmentDetails:
    expected: date
    observed: date

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.LATE_COMMITMENT


@dataclass(frozen=True)
class StaleRevisionDetails:
    expected: str
    observed: str

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.STALE_REVISION


@dataclass(frozen=True)
class UnresolvedIdentityDetails:
    expected: str | None
    observed: str

    @property
    def kind(self) -> AnomalyKind:
        return AnomalyKind.UNRESOLVED_IDENTITY


def _anomaly(
    subject_key: str,
    details: AnomalyDetails,
    severity: AnomalySeverity,
    evidence: tuple[EvidenceRef, ...],
    policy_id: str,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly:
    # The public Anomaly constructor accepts the structural AnomalyDetails protocol.
    return Anomaly(
        subject_key,
        details,
        severity,
        AnomalyStatus.OPEN,
        evidence,
        policy_id,
        provenance,
        detected_at,
    )


def detect_expected_observed_anomalies(
    state: ExpectedObservedState,
    *,
    policy: ExpectedObservedAnomalyPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> tuple[Anomaly, ...]:
    """Detect deterministic state deviations without predicting or acting."""
    expected = state.expected
    observed = state.observed
    evidence = _state_evidence(state)
    subject_key = _state_subject_key(state)
    anomalies: list[Anomaly] = []

    missing_policy = policy.missing_purchase_order
    if observed is None or observed.ordered_quantity <= Decimal(0):
        if expected.required_quantity > missing_policy.minimum_required_quantity:
            anomalies.append(
                _anomaly(
                    subject_key,
                    MissingPurchaseOrderDetails(
                        expected.required_quantity,
                        None if observed is None else observed.ordered_quantity,
                    ),
                    AnomalySeverity.WARNING,
                    evidence,
                    missing_policy.policy_id,
                    provenance,
                    detected_at,
                )
            )
    elif (
        abs(observed.ordered_quantity - expected.required_quantity)
        > policy.quantity_mismatch.tolerance
    ):
        anomalies.append(
            _anomaly(
                subject_key,
                QuantityMismatchDetails(expected.required_quantity, observed.ordered_quantity),
                AnomalySeverity.WARNING,
                evidence,
                policy.quantity_mismatch.policy_id,
                provenance,
                detected_at,
            )
        )

    if observed is None:
        return tuple(anomalies)

    if observed.substituted_quantity > policy.substitution.tolerance:
        anomalies.append(
            _anomaly(
                subject_key,
                SubstitutionDetails(Decimal(0), observed.substituted_quantity),
                AnomalySeverity.WARNING,
                evidence,
                policy.substitution.policy_id,
                provenance,
                detected_at,
            )
        )

    coverage_policy = policy.coverage_gap
    if (
        coverage_policy.flag_non_current and observed.freshness is not StateFreshness.CURRENT
    ) or observed.unknown_quantity > coverage_policy.unknown_quantity_tolerance:
        anomalies.append(
            _anomaly(
                subject_key,
                CoverageGapDetails(expected.required_quantity, observed.unknown_quantity),
                AnomalySeverity.INFO,
                evidence,
                coverage_policy.policy_id,
                provenance,
                detected_at,
            )
        )

    return tuple(anomalies)


def _state_subject_key(state: ExpectedObservedState) -> str:
    scope = state.expected.scope
    return (
        f"{scope.tenant_id}/{scope.project_id}/{scope.site_id}/"
        f"{scope.version}:{state.expected.canonical_key}"
    )


def _state_evidence(state: ExpectedObservedState) -> tuple[EvidenceRef, ...]:
    evidence = list(state.expected.evidence)
    if state.observed is not None:
        evidence.extend(state.observed.evidence)
    return tuple({ref.evidence_id: ref for ref in evidence}.values())


def detect_quantity_mismatch(
    subject_key: str,
    expected: Decimal,
    observed: Decimal,
    evidence: tuple[EvidenceRef, ...],
    *,
    policy: QuantityMismatchPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    _validate_comparison("expected quantity", expected)
    _validate_comparison("observed quantity", observed)
    if abs(observed - expected) <= policy.tolerance:
        return None
    return _anomaly(
        subject_key,
        QuantityMismatchDetails(expected, observed),
        AnomalySeverity.WARNING,
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
    policy: PriceDeviationPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    _validate_comparison("expected price", expected)
    _validate_comparison("observed price", observed)
    if abs(observed - expected) <= policy.tolerance:
        return None
    return _anomaly(
        subject_key,
        PriceDeviationDetails(expected, observed),
        AnomalySeverity.WARNING,
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
    policy: LateCommitmentPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    if observed <= expected + policy.tolerance:
        return None
    return _anomaly(
        subject_key,
        LateCommitmentDetails(expected, observed),
        AnomalySeverity.WARNING,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )


def detect_stale_revision(
    subject_key: str,
    expected: str,
    observed: str,
    evidence: tuple[EvidenceRef, ...],
    *,
    policy: StaleRevisionPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly | None:
    if not expected.strip() or not observed.strip():
        raise ValueError("expected and observed revisions are required")
    if observed == expected:
        return None
    return _anomaly(
        subject_key,
        StaleRevisionDetails(expected, observed),
        AnomalySeverity.WARNING,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )


def detect_unresolved_identity(
    subject_key: str,
    observed: str,
    evidence: tuple[EvidenceRef, ...],
    *,
    expected: str | None,
    policy: UnresolvedIdentityPolicy,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly:
    if not observed.strip():
        raise ValueError("observed identity mention is required")
    return _anomaly(
        subject_key,
        UnresolvedIdentityDetails(expected, observed),
        AnomalySeverity.WARNING,
        evidence,
        policy.policy_id,
        provenance,
        detected_at,
    )
