"""Deterministic brief construction and explicit human approval/save policy."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from procurement_intelligence_lab.application.corpus_agent_tools import (
    CorpusAgentTools,
    InvestigateToolArgs,
    SourceToolArgs,
    ToolExecutionError,
)
from procurement_intelligence_lab.application.corpus_investigation import (
    InvestigationRequest,
    InvestigationResult,
)
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefIntegrityError,
    BriefNotFound,
    ReviewBrief,
    ReviewReceipt,
    SavedBrief,
    canonical,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.ports.briefs import BriefStore
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError


def brief_facts(result: InvestigationResult) -> str:
    """No free-text factual claims: exact governed values and retained uncertainty."""
    decision = result.governed.decision
    return canonical(
        {
            "item": decision.canonical_key,
            "as_of": decision.as_of.isoformat(),
            "snapshot_id": result.snapshot_id,
            "status": result.assessment.status.value,
            "reason": result.assessment.reason.value if result.assessment.reason else None,
            "required_quantity": str(result.governed.expected.required_quantity)
            if result.governed.expected
            else None,
            "ordered_quantity": str(result.ordered_quantity)
            if result.ordered_quantity is not None
            else None,
            "unit": decision.unit,
            "governance_status": decision.status.value,
            "governance_policy_id": decision.policy_id,
            "governance_decision_id": decision.decision_id,
            "assessment_id": result.assessment.assessment_id,
            "policy_id": result.assessment.policy_id,
            "policy_digest": result.assessment.policy_digest,
            "governance_dispositions": dict(decision.dispositions),
            "input_dispositions": dict(result.assessment.input_dispositions),
            "evidence_by_role": {
                role: [ref.evidence_id for ref in refs]
                for role, refs in result.assessment.evidence_by_role
            },
            "evidence": [ref.as_dict() for ref in result.evidence],
        }
    )


@dataclass
class BriefReviewService:
    tools: CorpusAgentTools
    store: BriefStore
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    approval_ttl: timedelta = timedelta(hours=1)

    def __post_init__(self) -> None:
        if type(self.approval_ttl) is not timedelta or self.approval_ttl <= timedelta(0):
            raise ValueError("approval TTL must be positive")

    def draft(
        self, run_id: str, args: InvestigateToolArgs, *, context: RequestContext
    ) -> ReviewBrief:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        run = self.tools.runs.resume(run_id, context=context)
        try:
            version = self.get(run_id, None, context=context).version + 1
        except BriefNotFound:
            version = 1
        result = self.tools.investigate(run_id, args, context=context)
        if result.evidence:
            self.tools.source(
                run_id, SourceToolArgs(result.evidence[0].evidence_id), context=context
            )
        brief = ReviewBrief(
            str(uuid4()),
            run,
            version,
            args.request.canonical_key,
            args.request.as_of,
            result.snapshot_id,
            brief_facts(result),
            self.clock(),
        )
        self.store.put(brief, context=context)
        return brief

    def get(self, run_id: str, brief_id: str | None, *, context: RequestContext) -> ReviewBrief:
        context.require(Permission.READ_EVIDENCE)
        run = self.tools.runs.resume(run_id, context=context)
        brief = self.store.get(run_id, brief_id, context=context)
        if brief.run != run:
            raise BriefIntegrityError("stored brief differs from authoritative run binding")
        return brief

    def review(
        self, run_id: str, brief_id: str, digest: str, decision: str, *, context: RequestContext
    ) -> ReviewReceipt:
        context.require(Permission.REVIEW)
        brief = self.get(run_id, brief_id, context=context)
        if brief.digest != digest:
            raise BriefConflict("review digest differs from exact brief")
        now = self.clock()
        return self.store.decide(
            ReviewReceipt(
                brief_id,
                run_id,
                digest,
                context.principal_id,
                decision,
                now,
                now + self.approval_ttl,
            ),
            context=context,
        )

    def saved(self, run_id: str, brief_id: str, *, context: RequestContext) -> SavedBrief | None:
        """Read authoritative save evidence without granting action permission."""
        return self.store.saved(self.get(run_id, brief_id, context=context), context=context)

    def receipt(
        self, run_id: str, brief_id: str, *, context: RequestContext
    ) -> ReviewReceipt | None:
        return self.store.receipt(self.get(run_id, brief_id, context=context), context=context)

    def save(
        self,
        run_id: str,
        brief_id: str,
        digest: str,
        idempotency_key: str,
        *,
        context: RequestContext,
    ) -> SavedBrief:
        context.require(Permission.REVIEW)
        context.require(Permission.ACT)
        context.require(Permission.READ_EVIDENCE)
        brief = self.get(run_id, brief_id, context=context)
        if (digest, idempotency_key) != (brief.digest, brief.idempotency_key):
            raise BriefConflict("save digest/key differs from exact brief")
        try:
            current = self.tools.investigator.investigate(
                InvestigationRequest(brief.item, brief.as_of), context=context
            )
        except CorpusAdmissionError as error:
            raise ToolExecutionError("corpus_admission_failed") from error
        if current.snapshot_id != brief.snapshot_id or brief_facts(current) != brief.content_json:
            raise BriefConflict("evidence or core facts changed since review")
        return self.store.save(brief, self.clock, context=context)
