"""Validated retained recovery, independent of source/config and executor construction."""

from collections.abc import Callable
from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.processing.contracts import (
    AttemptSuccess,
    JobHistoryPage,
    JobView,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobConflictError,
    JobIntegrityError,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.local_prefix_jobs import LocalPrefixJobs


@dataclass(frozen=True)
class LocalPrefixJobReader:
    journal: LocalPrefixJobs
    validate_completed: Callable[[CompletedPrefixSnapshot], None]

    def _validate(self, success: AttemptSuccess | None) -> None:
        if success is not None:
            try:
                self.validate_completed(success.completed)
            except (SemanticContractError, ValueError, TypeError, KeyError, AttributeError):
                raise JobIntegrityError("retained job domain evidence is invalid") from None

    def show(self, scope: StateScope, job_id: str) -> JobView:
        view = self.journal.load(scope, job_id)
        self._validate(view.latest.transition.success)
        return view

    def history(
        self, scope: StateScope, job_id: str, *, limit: int = 100, after_sequence: int = 0
    ) -> JobHistoryPage:
        page = self.journal.history(scope, job_id, limit=limit, after_sequence=after_sequence)
        for receipt in page.receipts:
            self._validate(receipt.transition.success)
        return page

    def result(self, scope: StateScope, job_id: str) -> AttemptSuccess:
        success = self.show(scope, job_id).latest.transition.success
        if success is None:
            raise JobConflictError("job has no positively recorded successful result")
        return success

    def content(self, scope: StateScope, job_id: str) -> bytes:
        self.result(scope, job_id)
        return self.journal.content(scope, job_id)
