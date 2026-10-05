"""Persistence port for human reconciliation decisions."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.domains.procurement.review_reconciliation import (
    HumanReconciliationDecision,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext


class ReconciliationReviewStore(Protocol):
    def record(
        self, decision: HumanReconciliationDecision, *, context: RequestContext
    ) -> HumanReconciliationDecision: ...
    def latest(
        self, subject_key: str, as_of: datetime, *, context: RequestContext
    ) -> HumanReconciliationDecision | None: ...
    def for_brief(
        self, brief_id: str, *, context: RequestContext
    ) -> HumanReconciliationDecision | None: ...
