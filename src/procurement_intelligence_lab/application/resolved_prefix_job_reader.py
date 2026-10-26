"""Validated retained recovery, independent of source/config and executor construction."""

from collections.abc import Callable
from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    ResolvedAttemptSuccess,
    ResolvedJobHistoryPage,
    ResolvedJobView,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobConflictError,
    ResolvedJobIntegrityError,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.resolved_prefix_jobs import ResolvedPrefixJobs


@dataclass(frozen=True)
class ResolvedPrefixJobReader:
    journal: ResolvedPrefixJobs
    validate_completed: Callable[[CompletedResolvedPrefixSnapshot], None]

    def _validate(self, success: ResolvedAttemptSuccess | None) -> None:
        if success is not None:
            try:
                self.validate_completed(success.completed)
            except (SemanticContractError, ValueError, TypeError, KeyError, AttributeError):
                raise ResolvedJobIntegrityError("retained job domain evidence is invalid") from None

    def show(self, scope: StateScope, job_id: str) -> ResolvedJobView:
        view = self.journal.load(scope, job_id)
        self._validate(view.latest.transition.success)
        return view

    def history(
        self, scope: StateScope, job_id: str, *, limit: int = 100, after_sequence: int = 0
    ) -> ResolvedJobHistoryPage:
        page = self.journal.history(scope, job_id, limit=limit, after_sequence=after_sequence)
        for receipt in page.receipts:
            self._validate(receipt.transition.success)
        return page

    def result(self, scope: StateScope, job_id: str) -> ResolvedAttemptSuccess:
        success = self.show(scope, job_id).latest.transition.success
        if success is None:
            raise ResolvedJobConflictError("job has no positively recorded successful result")
        return success

    def content(self, scope: StateScope, job_id: str) -> bytes:
        self.result(scope, job_id)
        return self.journal.content(scope, job_id)
