"""Public review evidence, keeping source claims and human correction records distinct."""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal

from procurement_intelligence_lab.application.document_stages import provenance_payload
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewTask,
    ReviewHistory,
)
from procurement_intelligence_lab.platform.semantics.values import SemanticValue


def value_payload(value: SemanticValue | None) -> dict[str, object]:
    if value is None:
        return {"type": "null", "value": None}
    encoded = (
        value.isoformat()
        if isinstance(value, (date, datetime))
        else str(value)
        if isinstance(value, Decimal)
        else value
    )
    return {"type": type(value).__name__.lower(), "value": encoded}


def task_payload(task: DocumentReviewTask) -> dict[str, object]:
    p = task.proposal
    context = p.previous.context
    assert context is not None  # Intrinsic task construction requires retained source context.
    return {
        "task_id": task.task_id,
        "digest": task.digest,
        "policy": task.policy_reference,
        "workflow": p.workflow.value,
        "scope": asdict(p.scope),
        "request_id": p.request_id,
        "snapshot_id": p.snapshot_id,
        "assertion_id": p.previous.assertion_id,
        "previous_value": value_payload(p.previous.value),
        "proposed_value": value_payload(p.proposed_value),
        "source_status": context.observation.status.value,
        "unit": context.observation.unit,
        "evidence": p.previous.evidence.as_dict(),
        "source_provenance": provenance_payload(context.provenance),
        "source_recorded_at": context.origin.recorded_at.isoformat(),
        "reason": p.reason,
        "proposer_id": p.proposer_id,
        "recorded_at": task.recorded_at.isoformat(),
    }


def history_payload(history: ReviewHistory) -> dict[str, object]:
    decision = history.decision
    body = task_payload(history.task)
    correction = None
    if history.correction_id is not None and decision is not None:
        correction = {
            "correction_id": history.correction_id,
            "corrects_assertion_id": history.task.proposal.previous.assertion_id,
            "review_task_id": history.task.task_id,
            "review_task_digest": history.task.digest,
            "review_decision_id": decision.decision_id,
            "value": value_payload(history.task.proposal.proposed_value),
            "unit": body["unit"],
            "effective_at": decision.effective_at.isoformat(),
            "recomputation_required": True,
            "downstream_status": "not_evaluated",
            "governing_state_updated": False,
        }
    return {
        "task": body,
        "decision": None
        if decision is None
        else {
            "decision_id": decision.decision_id,
            "task_id": decision.command.task_id,
            "task_digest": decision.command.task_digest,
            "request_id": decision.command.request_id,
            "outcome": decision.command.outcome.value,
            "reviewer_id": decision.command.reviewer_id,
            "reason": decision.command.reason,
            "recorded_at": decision.recorded_at.isoformat(),
            "effective_at": decision.effective_at.isoformat(),
        },
        "correction": correction,
    }
