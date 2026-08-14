from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.domain.anomalies import (
    Anomaly,
    AnomalyKind,
    AnomalyPolicy,
    AnomalySeverity,
    AnomalyStatus,
    detect_expected_observed_anomalies,
    detect_late_commitment,
    detect_price_deviation,
    detect_quantity_mismatch,
)
from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.domain.state import (
    ExpectedObservedState,
    ExpectedRequirement,
    ObservedProcurement,
    StateFreshness,
    StateScope,
)


@pytest.fixture
def evidence() -> tuple[EvidenceRef, ...]:
    return (EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B")),)


@pytest.fixture
def detected_at() -> datetime:
    return datetime(2026, 1, 10, tzinfo=UTC)


@pytest.fixture
def provenance() -> DecisionProvenance:
    from procurement_intelligence_lab.domain.provenance import local_provenance_context

    return DecisionProvenance(
        local_provenance_context(),
        "test-anomaly-detector",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="test-v1",
    )


def test_anomaly_ids_are_stable_and_evidence_backed(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    anomaly = Anomaly(
        "GPU-A",
        AnomalyKind.QUANTITY_MISMATCH,
        Decimal(4),
        Decimal(8),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        evidence,
        "default-v1",
        provenance,
        detected_at,
    )

    equivalent = Anomaly(
        "GPU-A",
        AnomalyKind.QUANTITY_MISMATCH,
        Decimal(4),
        Decimal(8),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        evidence,
        "default-v1",
        provenance,
        detected_at,
    )
    different_evidence = Anomaly(
        "GPU-A",
        AnomalyKind.QUANTITY_MISMATCH,
        Decimal(4),
        Decimal(8),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        (EvidenceRef("other.xlsx", "hash", "BOM", 2, ("A", "B")),),
        "default-v1",
        provenance,
        detected_at,
    )
    multi_evidence = evidence + (EvidenceRef("bom.xlsx", "hash", "BOM", 3, ("C", "D")),)
    multi = Anomaly(
        "GPU-A",
        AnomalyKind.QUANTITY_MISMATCH,
        Decimal(4),
        Decimal(8),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        multi_evidence,
        "default-v1",
        provenance,
        detected_at,
    )
    reordered = Anomaly(
        "GPU-A",
        AnomalyKind.QUANTITY_MISMATCH,
        Decimal(4),
        Decimal(8),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        tuple(reversed(multi_evidence)),
        "default-v1",
        provenance,
        detected_at,
    )

    assert anomaly.anomaly_id == equivalent.anomaly_id
    assert multi.anomaly_id == reordered.anomaly_id
    assert anomaly.anomaly_id != different_evidence.anomaly_id
    assert anomaly.provenance.provenance_id == provenance.provenance_id


def test_quantity_tolerance_is_configurable(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    policy = AnomalyPolicy("quantity-v1", quantity_tolerance=Decimal(1))

    assert (
        detect_quantity_mismatch(
            "GPU-A",
            Decimal(4),
            Decimal(5),
            evidence,
            policy=policy,
            provenance=provenance,
            detected_at=detected_at,
        )
        is None
    )
    anomaly = detect_quantity_mismatch(
        "GPU-A",
        Decimal(4),
        Decimal(6),
        evidence,
        policy=policy,
        provenance=provenance,
        detected_at=detected_at,
    )

    assert anomaly is not None
    assert anomaly.kind is AnomalyKind.QUANTITY_MISMATCH
    assert anomaly.status is AnomalyStatus.OPEN


def test_price_and_schedule_comparisons_preserve_expected_observed_values(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    policy = AnomalyPolicy(
        "commercial-v1",
        price_tolerance=Decimal("0.05"),
        late_days_tolerance=2,
    )

    price = detect_price_deviation(
        "GPU-A",
        Decimal(100),
        Decimal(101),
        evidence,
        policy=policy,
        provenance=provenance,
        detected_at=detected_at,
    )
    late = detect_late_commitment(
        "PO-1",
        date(2026, 1, 10),
        date(2026, 1, 13),
        evidence,
        policy=policy,
        provenance=provenance,
        detected_at=detected_at,
    )

    assert price is not None
    assert price.expected == Decimal(100)
    assert price.observed == Decimal(101)
    assert late is not None
    assert late.kind is AnomalyKind.LATE_COMMITMENT


def test_anomalies_require_timezone_aware_detection_time(
    evidence: tuple[EvidenceRef, ...],
    provenance: DecisionProvenance,
) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Anomaly(
            "GPU-A",
            AnomalyKind.COVERAGE_GAP,
            None,
            None,
            AnomalySeverity.INFO,
            AnomalyStatus.OPEN,
            evidence,
            "coverage-v1",
            provenance,
            datetime(2026, 1, 10),  # noqa: DTZ001
        )


def _state_scope() -> StateScope:
    return StateScope("tenant", "project", "site", "bom-v1")


def test_state_orchestration_distinguishes_missing_po_from_quantity_mismatch(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    expected = ExpectedRequirement(
        "GPU-A",
        Decimal(4),
        _state_scope(),
        datetime(2026, 1, 1, tzinfo=UTC),
        evidence,
    )

    anomalies = detect_expected_observed_anomalies(
        ExpectedObservedState(expected, None),
        policy=AnomalyPolicy("state-v1"),
        provenance=provenance,
        detected_at=detected_at,
    )

    assert [anomaly.kind for anomaly in anomalies] == [AnomalyKind.MISSING_PO]
    assert anomalies[0].subject_key == "tenant/project/site/bom-v1:GPU-A"
    assert anomalies[0].evidence == evidence


def test_state_orchestration_preserves_scope_and_incomplete_observation(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    expected = ExpectedRequirement(
        "GPU-A",
        Decimal(4),
        _state_scope(),
        datetime(2026, 1, 1, tzinfo=UTC),
        evidence,
    )
    observed = ObservedProcurement(
        "GPU-A",
        Decimal(2),
        Decimal(1),
        Decimal(1),
        Decimal(0),
        Decimal(1),
        _state_scope(),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateFreshness.PARTIAL,
        evidence,
    )

    anomalies = detect_expected_observed_anomalies(
        ExpectedObservedState(expected, observed),
        policy=AnomalyPolicy("state-v1"),
        provenance=provenance,
        detected_at=detected_at,
    )

    assert [anomaly.kind for anomaly in anomalies] == [
        AnomalyKind.QUANTITY_MISMATCH,
        AnomalyKind.SUBSTITUTION,
        AnomalyKind.COVERAGE_GAP,
    ]
    assert anomalies[-1].severity is AnomalySeverity.INFO


def test_state_orchestration_tolerance_does_not_hide_nonzero_order(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
    provenance: DecisionProvenance,
) -> None:
    expected = ExpectedRequirement(
        "GPU-A",
        Decimal(4),
        _state_scope(),
        datetime(2026, 1, 1, tzinfo=UTC),
        evidence,
    )
    observed = ObservedProcurement(
        "GPU-A",
        Decimal(1),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        _state_scope(),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateFreshness.CURRENT,
        evidence,
    )

    anomalies = detect_expected_observed_anomalies(
        ExpectedObservedState(expected, observed),
        policy=AnomalyPolicy("state-v1", quantity_tolerance=Decimal(1)),
        provenance=provenance,
        detected_at=detected_at,
    )

    assert [anomaly.kind for anomaly in anomalies] == [AnomalyKind.QUANTITY_MISMATCH]
