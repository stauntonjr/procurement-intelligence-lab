"""Authorize evidence-bound human review; storage and domain policy are injected."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewTask,
    ReviewDecisionCommand,
    ReviewHistory,
    ReviewOutcome,
    ReviewProposal,
    ReviewWorkflow,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ReviewNotFoundError,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.platform.semantics.values import SemanticValue
from procurement_intelligence_lab.ports.assertion_archive import AssertionArchive
from procurement_intelligence_lab.ports.document_reviews import DocumentReviewJournal


def authorize(context: RequestContext, scope: StateScope, permission: Permission) -> None:
    context.require(permission)
    if (context.tenant_id, context.project_id, context.site_id) != (
        scope.tenant_id,
        scope.project_id,
        scope.site_id,
    ):
        raise ScopeAuthorizationError("document review scope is not authorized")


@dataclass(frozen=True)
class DocumentReviewService:
    archive: AssertionArchive
    journal: DocumentReviewJournal
    validate_proposal: Callable[[ReviewProposal], None]
    clock: Callable[[], datetime]

    def propose(
        self,
        *,
        scope: StateScope,
        request_id: str,
        snapshot_id: str,
        assertion_id: str,
        proposed_value: SemanticValue | None,
        reason: str,
        context: RequestContext,
        workflow: ReviewWorkflow = ReviewWorkflow.DOCUMENT_VALUE,
    ) -> DocumentReviewTask:
        authorize(context, scope, Permission.REVIEW)
        authorize(context, scope, Permission.READ_EVIDENCE)
        _, snapshot = self.archive.load(scope, snapshot_id)
        previous = next((a for a in snapshot.assertions if a.assertion_id == assertion_id), None)
        if previous is None:
            raise ReviewNotFoundError("assertion is not a member of the scoped snapshot")
        proposal = ReviewProposal(
            scope,
            request_id,
            snapshot_id,
            previous,
            proposed_value,
            reason,
            context.principal_id,
            workflow,
        )
        self.validate_proposal(proposal)
        return self.journal.propose(proposal, self.clock())

    def decide(
        self,
        *,
        scope: StateScope,
        request_id: str,
        task_id: str,
        task_digest: str,
        outcome: ReviewOutcome,
        reason: str,
        context: RequestContext,
    ) -> ReviewHistory:
        authorize(context, scope, Permission.REVIEW)
        authorize(context, scope, Permission.READ_EVIDENCE)
        current = self.journal.get(scope, task_id)
        self.validate_proposal(current.task.proposal)
        command = ReviewDecisionCommand(
            scope, request_id, task_id, task_digest, outcome, context.principal_id, reason
        )
        self.journal.decide(command, self.clock())
        return self.journal.get(scope, task_id)

    def show(
        self,
        scope: StateScope,
        task_id: str,
        *,
        context: RequestContext,
        as_of: datetime | None = None,
    ) -> ReviewHistory:
        authorize(context, scope, Permission.READ_EVIDENCE)
        result = self.journal.get(scope, task_id, as_of)
        self.validate_proposal(result.task.proposal)
        return result

    def history(
        self, scope: StateScope, *, context: RequestContext, as_of: datetime | None = None
    ) -> tuple[ReviewHistory, ...]:
        authorize(context, scope, Permission.READ_EVIDENCE)
        results = self.journal.history(scope, as_of)
        for result in results:
            self.validate_proposal(result.task.proposal)
        return results
