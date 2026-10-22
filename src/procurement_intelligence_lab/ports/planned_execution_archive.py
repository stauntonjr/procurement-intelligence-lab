"""Atomic completed execution retention; initialization is an adapter responsibility."""

from typing import Protocol

from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionHistoryPage,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class PlannedExecutionArchive(Protocol):
    def check_ready(self) -> None: ...
    def append(self, completed: CompletedPrefixSnapshot, content: bytes) -> ArchivedPrefix: ...
    def load(self, scope: StateScope, execution_digest: str) -> ArchivedPrefix: ...
    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ExecutionHistoryPage: ...
    def content(self, scope: StateScope, execution_digest: str) -> bytes: ...
