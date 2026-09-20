"""Pure append-only lifecycle projection for immutable anomaly detections."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly, AnomalyStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    ScopeContractError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class LifecycleEvidenceKind(StrEnum):
    REVIEW = "review"
    SUPPRESSION = "suppression"
    ADJUDICATION = "adjudication"
    COMPARISON = "comparison"
    REOPENING = "reopening"


@dataclass(frozen=True)
class AnomalyLifecycleEvent:
    event_id: str
    anomaly_id: str
    scope: StateScope
    previous_status: AnomalyStatus
    new_status: AnomalyStatus
    actor_ref: str
    occurred_at: datetime
    recorded_at: datetime
    reason: str
    evidence_ids: tuple[str, ...]
    evidence_kind: LifecycleEvidenceKind
    policy_id: str
    expected_prior_event_id: str | None

    def __post_init__(self) -> None:
        required = {
            "event ID": self.event_id,
            "anomaly ID": self.anomaly_id,
            "actor": self.actor_ref,
            "reason": self.reason,
            "policy": self.policy_id,
        }
        for name, value in required.items():
            if not value.strip():
                raise SemanticContractError(f"lifecycle {name} is required")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise SemanticContractError("lifecycle evidence IDs are required")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise SemanticContractError("lifecycle evidence IDs must be unique")
        if self.occurred_at.tzinfo is None or self.recorded_at.tzinfo is None:
            raise TemporalContractError("lifecycle timestamps must be timezone-aware")
        if self.occurred_at > self.recorded_at:
            raise TemporalContractError("lifecycle event cannot occur in the future")
        if self.expected_prior_event_id is not None and not self.expected_prior_event_id.strip():
            raise SemanticContractError("expected prior event ID must not be blank")

    @property
    def event_identity(self) -> str:
        return stable_id(
            "anomaly-lifecycle-event",
            self.event_id,
            self.anomaly_id,
            self.scope,
            self.previous_status.value,
            self.new_status.value,
            self.actor_ref,
            self.occurred_at.isoformat(),
            self.recorded_at.isoformat(),
            self.reason,
            tuple(sorted(self.evidence_ids)),
            self.evidence_kind.value,
            self.policy_id,
            self.expected_prior_event_id,
        )


def apply_lifecycle_event(
    anomaly: Anomaly,
    history: tuple[AnomalyLifecycleEvent, ...],
    event: AnomalyLifecycleEvent,
) -> Anomaly:
    """Validate append-only history and project one event without mutating detection evidence."""
    _require_target(anomaly, event)
    status, prior_id, prior_time, by_id = _validate_history(anomaly, history)
    prior = by_id.get(event.event_id)
    if prior is not None:
        if prior != event:
            raise SemanticContractError("lifecycle event ID was reused with different meaning")
        return replace(anomaly, status=status)
    if event.expected_prior_event_id != prior_id:
        raise SemanticContractError("lifecycle event predecessor does not match current history")
    if event.previous_status is not status:
        raise SemanticContractError("lifecycle event previous status does not match projection")
    if event.occurred_at < prior_time:
        raise TemporalContractError("lifecycle events must be chronological")
    _validate_transition(event)
    return replace(anomaly, status=event.new_status)


def _validate_history(
    anomaly: Anomaly,
    history: tuple[AnomalyLifecycleEvent, ...],
) -> tuple[
    AnomalyStatus,
    str | None,
    datetime,
    dict[str, AnomalyLifecycleEvent],
]:
    status = anomaly.status
    prior_id: str | None = None
    prior_time = anomaly.detected_at
    by_id: dict[str, AnomalyLifecycleEvent] = {}
    for event in history:
        _require_target(anomaly, event)
        existing = by_id.get(event.event_id)
        if existing is not None:
            if existing != event:
                raise SemanticContractError("lifecycle event ID was reused with different meaning")
            continue
        if event.expected_prior_event_id != prior_id:
            raise SemanticContractError("lifecycle history predecessor chain is invalid")
        if event.previous_status is not status:
            raise SemanticContractError("lifecycle history status chain is invalid")
        if event.occurred_at < prior_time:
            raise TemporalContractError("lifecycle history must be chronological")
        _validate_transition(event)
        by_id[event.event_id] = event
        prior_id = event.event_id
        prior_time = event.occurred_at
        status = event.new_status
    return status, prior_id, prior_time, by_id


def _require_target(anomaly: Anomaly, event: AnomalyLifecycleEvent) -> None:
    if event.anomaly_id != anomaly.anomaly_id:
        raise SemanticContractError("lifecycle event targets a different anomaly")
    if event.scope != anomaly.scope:
        raise ScopeContractError("lifecycle event scope does not match anomaly scope")


def _validate_transition(event: AnomalyLifecycleEvent) -> None:
    allowed = {
        AnomalyStatus.OPEN: frozenset(
            {AnomalyStatus.IN_REVIEW, AnomalyStatus.SUPPRESSED, AnomalyStatus.RESOLVED}
        ),
        AnomalyStatus.IN_REVIEW: frozenset(
            {AnomalyStatus.OPEN, AnomalyStatus.SUPPRESSED, AnomalyStatus.RESOLVED}
        ),
        AnomalyStatus.SUPPRESSED: frozenset(
            {AnomalyStatus.OPEN, AnomalyStatus.IN_REVIEW, AnomalyStatus.RESOLVED}
        ),
        AnomalyStatus.RESOLVED: frozenset({AnomalyStatus.OPEN}),
    }
    if event.new_status not in allowed[event.previous_status]:
        raise SemanticContractError(
            f"unsupported anomaly lifecycle transition: "
            f"{event.previous_status.value}->{event.new_status.value}"
        )
    if (
        event.new_status is AnomalyStatus.SUPPRESSED
        and event.evidence_kind is not LifecycleEvidenceKind.SUPPRESSION
    ):
        raise SemanticContractError("suppression requires suppression evidence")
    if event.new_status is AnomalyStatus.RESOLVED and event.evidence_kind not in {
        LifecycleEvidenceKind.ADJUDICATION,
        LifecycleEvidenceKind.COMPARISON,
    }:
        raise SemanticContractError("resolution requires adjudication or comparison evidence")
    if (
        event.new_status is AnomalyStatus.OPEN
        and event.evidence_kind is not LifecycleEvidenceKind.REOPENING
    ):
        raise SemanticContractError("reopening requires explicit reopening evidence")
    if (
        event.new_status is AnomalyStatus.IN_REVIEW
        and event.evidence_kind is not LifecycleEvidenceKind.REVIEW
    ):
        raise SemanticContractError("review transition requires review evidence")
