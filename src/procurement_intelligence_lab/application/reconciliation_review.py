"""Exact human reconciliation review over persisted procurement assessments."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from procurement_intelligence_lab.application.corpus_agent_tools import Investigator
from procurement_intelligence_lab.application.corpus_investigation import (
    InvestigationRequest,
    InvestigationResult,
)
from procurement_intelligence_lab.application.exact_brief_review import (
    BriefReviewService,
    brief_facts,
)
from procurement_intelligence_lab.domains.procurement.review_reconciliation import (
    HumanReconciliationDecision,
    ReconciliationReviewOutcome,
    prospective_decision_id,
)
from procurement_intelligence_lab.platform.semantics.briefs import BriefConflict
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.ports.reconciliation_reviews import ReconciliationReviewStore


@dataclass(frozen=True)
class ReconciliationReviewResult:
    decision: HumanReconciliationDecision
    current: InvestigationResult


@dataclass
class ReconciliationReviewService:
    briefs: BriefReviewService
    investigator: Investigator
    store: ReconciliationReviewStore
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def reconcile(
        self,
        run_id: str,
        brief_id: str,
        digest: str,
        outcome: str,
        selected_claim_id: str,
        rationale: str,
        *,
        context: RequestContext,
    ) -> ReconciliationReviewResult:
        context.require(Permission.REVIEW)
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        brief = self.briefs.get(run_id, brief_id, context=context)
        if brief.digest != digest:
            raise BriefConflict("reconciliation digest differs from exact assessment")
        fresh = self.investigator.investigate(
            InvestigationRequest(brief.item, brief.as_of), context=context
        )
        if fresh.snapshot_id != brief.snapshot_id or brief_facts(fresh) != brief.content_json:
            raise BriefConflict("evidence or core facts changed since assessment")
        all_candidates = fresh.governed.decision.governing + fresh.governed.decision.losing
        dispositions = dict(fresh.governed.decision.dispositions)
        candidates = tuple(
            item
            for item in all_candidates
            if dispositions[item.claim_id] == "conflicting: no value established"
        )
        parsed = ReconciliationReviewOutcome(outcome)
        if parsed is ReconciliationReviewOutcome.SELECT_GOVERNING_REVISION and len(candidates) != 2:
            raise BriefConflict(
                "governing selection requires exactly two eligible conflicting candidates"
            )
        candidate_ids = tuple(item.claim_id for item in candidates)
        now = self.clock()
        scope = StateScope(
            context.tenant_id, context.project_id, context.site_id, fresh.snapshot_id
        )
        if not candidates or any(
            (item.scope.tenant_id, item.scope.project_id, item.scope.site_id)
            != (context.tenant_id, context.project_id, context.site_id)
            for item in candidates
        ):
            raise BriefConflict("assessment candidates do not share one exact scope")
        selected = selected_claim_id or None
        values = dict(
            brief_id=brief.brief_id,
            brief_digest=brief.digest,
            subject_key=brief.item,
            scope=scope,
            outcome=parsed,
            candidate_claim_ids=candidate_ids,
            selected_claim_id=selected,
            rationale=rationale,
            reviewer_id=context.principal_id,
            policy_id="human-required-quantity/v1",
            recorded_at=now,
            effective_at=now,
            evidence=tuple(item.evidence for item in candidates),
        )
        decision = HumanReconciliationDecision(
            decision_id=prospective_decision_id(**values), **values
        )
        durable = self.store.record(decision, context=context)
        current = self.investigator.investigate(
            InvestigationRequest(brief.item, now), context=context
        )
        return ReconciliationReviewResult(durable, current)


def reconciliation_result_dto(result: ReconciliationReviewResult) -> dict[str, object]:
    return {
        "decision": {
            "decision_id": result.decision.decision_id,
            "outcome": result.decision.outcome.value,
            "selected_claim_id": result.decision.selected_claim_id,
            "rationale": result.decision.rationale,
            "effective_at": result.decision.effective_at.isoformat(),
            "subject_key": result.decision.subject_key,
        },
        "current_assessment": json.loads(brief_facts(result.current)),
    }
