from datetime import UTC, datetime
from pathlib import Path

import pytest

from procurement_intelligence_lab.application.reconciliation_review import (
    ReconciliationReviewService,
)
from procurement_intelligence_lab.interfaces.workflow import compose_services
from procurement_intelligence_lab.platform.semantics.briefs import BriefConflict
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.platform.semantics.workflows import WorkflowRequest

CONTEXT = RequestContext(
    "reviewer",
    "synthetic-tenant",
    "atlas",
    "lab",
    frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE, Permission.REVIEW, Permission.ACT}),
    "trace",
)
AS_OF = datetime(2026, 10, 1, tzinfo=UTC)
NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)


def test_service_records_exact_selection_and_recomputes_current_state(tmp_path: Path) -> None:
    composition = compose_services(tmp_path / "review.sqlite")
    view = composition.runtime.start(WorkflowRequest("GPU-C", AS_OF), context=CONTEXT)
    facts = __import__("json").loads(view.brief.content_json)
    candidates = [item for item in facts["governance_candidates"] if item["eligible"]]
    assert len(candidates) == 2
    service: ReconciliationReviewService = composition.reconciliation
    service.clock = lambda: NOW
    result = service.reconcile(
        view.run_id,
        view.brief.brief_id,
        view.brief.digest,
        "select_governing_revision",
        candidates[1]["claim_id"],
        "Revision B is the approved requirement for this scoped item.",
        context=CONTEXT,
    )
    assert result.decision.selected_claim_id == candidates[1]["claim_id"]
    assert result.decision.effective_at == NOW
    assert result.current.governed.expected is not None
    assert (
        composition.reconciliation_store.record(result.decision, context=CONTEXT) == result.decision
    )


def test_service_rejects_stale_digest_and_unknown_candidate(tmp_path: Path) -> None:
    composition = compose_services(tmp_path / "review.sqlite")
    view = composition.runtime.start(WorkflowRequest("GPU-C", AS_OF), context=CONTEXT)
    composition.reconciliation.clock = lambda: NOW
    with pytest.raises(BriefConflict):
        composition.reconciliation.reconcile(
            view.run_id,
            view.brief.brief_id,
            "0" * 64,
            "select_governing_revision",
            "unknown",
            "Valid rationale.",
            context=CONTEXT,
        )
