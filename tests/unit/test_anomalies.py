from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.domain.anomalies import (
    Anomaly,
    AnomalyKind,
    AnomalyPolicy,
    AnomalySeverity,
    AnomalyStatus,
    detect_late_commitment,
    detect_price_deviation,
    detect_quantity_mismatch,
)
from procurement_intelligence_lab.domain.bom import EvidenceRef


@pytest.fixture
def evidence() -> tuple[EvidenceRef, ...]:
    return (EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B")),)


@pytest.fixture
def detected_at() -> datetime:
    return datetime(2026, 1, 10, tzinfo=UTC)


def test_anomaly_ids_are_stable_and_evidence_backed(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
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
        detected_at,
    )

    assert anomaly.anomaly_id == equivalent.anomaly_id
    assert anomaly.anomaly_id != different_evidence.anomaly_id


def test_quantity_tolerance_is_configurable(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
) -> None:
    policy = AnomalyPolicy("quantity-v1", quantity_tolerance=Decimal(1))

    assert (
        detect_quantity_mismatch(
            "GPU-A",
            Decimal(4),
            Decimal(5),
            evidence,
            policy=policy,
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
        detected_at=detected_at,
    )

    assert anomaly is not None
    assert anomaly.kind is AnomalyKind.QUANTITY_MISMATCH
    assert anomaly.status is AnomalyStatus.OPEN


def test_price_and_schedule_comparisons_preserve_expected_observed_values(
    evidence: tuple[EvidenceRef, ...],
    detected_at: datetime,
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
        detected_at=detected_at,
    )
    late = detect_late_commitment(
        "PO-1",
        date(2026, 1, 10),
        date(2026, 1, 13),
        evidence,
        policy=policy,
        detected_at=detected_at,
    )

    assert price is not None
    assert price.expected == Decimal(100)
    assert price.observed == Decimal(101)
    assert late is not None
    assert late.kind is AnomalyKind.LATE_COMMITMENT


def test_anomalies_require_timezone_aware_detection_time(
    evidence: tuple[EvidenceRef, ...],
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
            datetime(2026, 1, 10),  # noqa: DTZ001
        )
