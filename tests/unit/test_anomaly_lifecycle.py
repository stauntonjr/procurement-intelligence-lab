import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.resources import files

import pytest

from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.domains.procurement.anomalies import QuantityMismatchDetails
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.platform.semantics.anomalies import (
    Anomaly,
    AnomalySeverity,
    AnomalyStatus,
)
from procurement_intelligence_lab.platform.semantics.anomaly_lifecycle import (
    AnomalyLifecycleEvent,
    LifecycleEvidenceKind,
    apply_lifecycle_event,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

TIME = datetime(2026, 9, 19, 12, tzinfo=UTC)
SCOPE = StateScope("tenant", "project", "site", "governed-v1")
SOURCE = EvidenceRef("orders", "hash", RecordLocation("orders", "line-1"))


def _anomaly() -> Anomaly:
    provenance = DecisionProvenance(
        local_provenance_context(),
        "quantity-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
    )
    return Anomaly(
        "GPU-A",
        QuantityMismatchDetails(Decimal(4), Decimal(2)),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        (SOURCE,),
        "quantity/v1",
        provenance,
        TIME,
        SCOPE,
    )


def _event(
    anomaly: Anomaly,
    previous: AnomalyStatus,
    new: AnomalyStatus,
    *,
    event_id: str = "event-1",
    prior: str | None = None,
    occurred_at: datetime = TIME + timedelta(minutes=1),
    recorded_at: datetime = TIME + timedelta(minutes=2),
    evidence_kind: LifecycleEvidenceKind = LifecycleEvidenceKind.REVIEW,
) -> AnomalyLifecycleEvent:
    return AnomalyLifecycleEvent(
        event_id=event_id,
        anomaly_id=anomaly.anomaly_id,
        scope=anomaly.scope,
        previous_status=previous,
        new_status=new,
        actor_ref="reviewer:synthetic",
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        reason="synthetic lifecycle decision",
        evidence_ids=("lifecycle-evidence-1",),
        evidence_kind=evidence_kind,
        policy_id="anomaly-lifecycle/v1",
        expected_prior_event_id=prior,
    )


@pytest.mark.parametrize(
    ("previous", "new", "evidence_kind"),
    [
        (AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW, LifecycleEvidenceKind.REVIEW),
        (AnomalyStatus.OPEN, AnomalyStatus.SUPPRESSED, LifecycleEvidenceKind.SUPPRESSION),
        (AnomalyStatus.OPEN, AnomalyStatus.RESOLVED, LifecycleEvidenceKind.ADJUDICATION),
        (AnomalyStatus.IN_REVIEW, AnomalyStatus.OPEN, LifecycleEvidenceKind.REOPENING),
        (AnomalyStatus.IN_REVIEW, AnomalyStatus.SUPPRESSED, LifecycleEvidenceKind.SUPPRESSION),
        (AnomalyStatus.IN_REVIEW, AnomalyStatus.RESOLVED, LifecycleEvidenceKind.COMPARISON),
        (AnomalyStatus.SUPPRESSED, AnomalyStatus.OPEN, LifecycleEvidenceKind.REOPENING),
        (AnomalyStatus.SUPPRESSED, AnomalyStatus.IN_REVIEW, LifecycleEvidenceKind.REVIEW),
        (AnomalyStatus.SUPPRESSED, AnomalyStatus.RESOLVED, LifecycleEvidenceKind.ADJUDICATION),
        (AnomalyStatus.RESOLVED, AnomalyStatus.OPEN, LifecycleEvidenceKind.REOPENING),
    ],
)
def test_permitted_lifecycle_transitions(
    previous: AnomalyStatus,
    new: AnomalyStatus,
    evidence_kind: LifecycleEvidenceKind,
) -> None:
    anomaly = replace(_anomaly(), status=previous)
    projected = apply_lifecycle_event(
        anomaly,
        (),
        _event(anomaly, previous, new, evidence_kind=evidence_kind),
    )

    assert projected.status is new
    assert projected.anomaly_id == anomaly.anomaly_id
    assert projected.evidence == anomaly.evidence
    assert anomaly.status is previous


@pytest.mark.parametrize(
    ("previous", "new"),
    [
        (AnomalyStatus.OPEN, AnomalyStatus.OPEN),
        (AnomalyStatus.IN_REVIEW, AnomalyStatus.IN_REVIEW),
        (AnomalyStatus.SUPPRESSED, AnomalyStatus.SUPPRESSED),
        (AnomalyStatus.RESOLVED, AnomalyStatus.RESOLVED),
        (AnomalyStatus.RESOLVED, AnomalyStatus.IN_REVIEW),
        (AnomalyStatus.RESOLVED, AnomalyStatus.SUPPRESSED),
    ],
)
def test_self_and_illegal_transitions_fail(previous: AnomalyStatus, new: AnomalyStatus) -> None:
    anomaly = replace(_anomaly(), status=previous)
    with pytest.raises(ValueError, match="transition"):
        apply_lifecycle_event(anomaly, (), _event(anomaly, previous, new))


def test_resolution_and_suppression_require_typed_evidence() -> None:
    anomaly = _anomaly()
    with pytest.raises(ValueError, match="resolution.*evidence"):
        apply_lifecycle_event(
            anomaly,
            (),
            _event(
                anomaly,
                AnomalyStatus.OPEN,
                AnomalyStatus.RESOLVED,
                evidence_kind=LifecycleEvidenceKind.REVIEW,
            ),
        )
    with pytest.raises(ValueError, match="suppression.*evidence"):
        apply_lifecycle_event(
            anomaly,
            (),
            _event(
                anomaly,
                AnomalyStatus.OPEN,
                AnomalyStatus.SUPPRESSED,
                evidence_kind=LifecycleEvidenceKind.REVIEW,
            ),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"actor_ref": ""}, "actor"),
        ({"reason": ""}, "reason"),
        ({"evidence_ids": ()}, "evidence"),
        ({"policy_id": ""}, "policy"),
        ({"occurred_at": datetime(2026, 9, 19, 12)}, "timezone-aware"),  # noqa: DTZ001
        ({"recorded_at": datetime(2026, 9, 19, 12)}, "timezone-aware"),  # noqa: DTZ001
        (
            {
                "occurred_at": TIME + timedelta(minutes=3),
                "recorded_at": TIME + timedelta(minutes=2),
            },
            "future",
        ),
    ],
)
def test_event_contract_rejects_incomplete_or_invalid_data(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(
            _event(_anomaly(), AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW),
            **changes,
        )


def test_replay_is_idempotent_but_conflicting_event_id_reuse_fails() -> None:
    anomaly = _anomaly()
    event = _event(anomaly, AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW)
    first = apply_lifecycle_event(anomaly, (), event)

    replayed = apply_lifecycle_event(anomaly, (event,), event)
    assert replayed == first

    conflicting = replace(event, reason="different meaning")
    with pytest.raises(ValueError, match="event ID"):
        apply_lifecycle_event(anomaly, (event,), conflicting)


def test_history_requires_exact_anomaly_scope_order_and_predecessor() -> None:
    anomaly = _anomaly()
    first = _event(anomaly, AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW)
    second = _event(
        anomaly,
        AnomalyStatus.IN_REVIEW,
        AnomalyStatus.SUPPRESSED,
        event_id="event-2",
        prior=first.event_id,
        occurred_at=TIME + timedelta(minutes=3),
        recorded_at=TIME + timedelta(minutes=4),
        evidence_kind=LifecycleEvidenceKind.SUPPRESSION,
    )

    assert apply_lifecycle_event(anomaly, (first,), second).status is AnomalyStatus.SUPPRESSED
    with pytest.raises(ValueError, match="predecessor"):
        apply_lifecycle_event(anomaly, (first,), replace(second, expected_prior_event_id="wrong"))
    with pytest.raises(ValueError, match="chronological"):
        apply_lifecycle_event(
            anomaly,
            (first,),
            replace(second, occurred_at=TIME, recorded_at=TIME + timedelta(minutes=4)),
        )
    with pytest.raises(ValueError, match="anomaly"):
        apply_lifecycle_event(anomaly, (first,), replace(second, anomaly_id="other"))
    with pytest.raises(ValueError, match="scope"):
        apply_lifecycle_event(
            anomaly,
            (first,),
            replace(second, scope=replace(SCOPE, site_id="other")),
        )


def test_service_replays_read_only_history_and_changed_anomaly_does_not_inherit_state() -> None:
    anomaly = _anomaly()
    first = _event(anomaly, AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW)
    second = _event(
        anomaly,
        AnomalyStatus.IN_REVIEW,
        AnomalyStatus.RESOLVED,
        event_id="event-2",
        prior=first.event_id,
        occurred_at=TIME + timedelta(minutes=3),
        recorded_at=TIME + timedelta(minutes=4),
        evidence_kind=LifecycleEvidenceKind.ADJUDICATION,
    )

    projected = AnomalyService.project_lifecycle(anomaly, (first, second))
    assert projected.status is AnomalyStatus.RESOLVED
    assert anomaly.status is AnomalyStatus.OPEN
    assert projected.evidence == anomaly.evidence

    changed = replace(anomaly, details=QuantityMismatchDetails(Decimal(4), Decimal(1)))
    assert changed.anomaly_id != anomaly.anomaly_id
    with pytest.raises(ValueError, match="anomaly"):
        AnomalyService.project_lifecycle(changed, (first, second))


def test_packaged_lifecycle_fixture_replays_without_public_write_authority() -> None:
    anomaly = _anomaly()
    payload = json.loads(
        files("procurement_intelligence_lab.examples")
        .joinpath("anomaly_lifecycle_v1.json")
        .read_text()
    )
    history = tuple(
        AnomalyLifecycleEvent(
            event_id=item["event_id"],
            anomaly_id=anomaly.anomaly_id,
            scope=anomaly.scope,
            previous_status=AnomalyStatus(item["previous_status"]),
            new_status=AnomalyStatus(item["new_status"]),
            actor_ref=item["actor_ref"],
            occurred_at=datetime.fromisoformat(item["occurred_at"]),
            recorded_at=datetime.fromisoformat(item["recorded_at"]),
            reason=item["reason"],
            evidence_ids=tuple(item["evidence_ids"]),
            evidence_kind=LifecycleEvidenceKind(item["evidence_kind"]),
            policy_id=item["policy_id"],
            expected_prior_event_id=item["expected_prior_event_id"],
        )
        for item in payload["events"]
    )

    projected = AnomalyService.project_lifecycle(anomaly, history)
    assert projected.status is AnomalyStatus.RESOLVED
    assert projected.anomaly_id == anomaly.anomaly_id
