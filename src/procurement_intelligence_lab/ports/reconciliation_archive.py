"""Explicit additive reconciliation persistence capability, independent of storage technology."""

from typing import Protocol

from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    ArchivedReconciliation,
    CompletedReconciliationSnapshot,
    ReconciliationHistoryPage,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class ReconciliationArchive(Protocol):
    def check_ready(self) -> None: ...
    def append(self, completed: CompletedReconciliationSnapshot) -> ArchivedReconciliation: ...
    def load(self, scope: StateScope, execution_digest: str) -> ArchivedReconciliation: ...
    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ReconciliationHistoryPage: ...
