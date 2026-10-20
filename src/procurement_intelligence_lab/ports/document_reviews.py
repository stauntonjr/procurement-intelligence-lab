"""Append-only document review commands; no source-update or operational-action authority."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewDecision,
    DocumentReviewTask,
    ReviewDecisionCommand,
    ReviewHistory,
    ReviewProposal,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class DocumentReviewJournal(Protocol):
    def propose(self, proposal: ReviewProposal, recorded_at: datetime) -> DocumentReviewTask: ...
    def decide(
        self, command: ReviewDecisionCommand, recorded_at: datetime
    ) -> DocumentReviewDecision: ...
    def get(
        self, scope: StateScope, task_id: str, as_of: datetime | None = None
    ) -> ReviewHistory: ...
    def history(
        self, scope: StateScope, as_of: datetime | None = None
    ) -> tuple[ReviewHistory, ...]: ...
