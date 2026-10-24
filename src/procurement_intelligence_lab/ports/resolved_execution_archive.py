"""Atomic retention of completed resolved-prefix evidence behind a neutral port."""

from typing import Protocol

from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
    CompletedResolvedPrefixSnapshot,
    ResolvedExecutionHistoryPage,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class ResolvedExecutionArchive(Protocol):
    def check_ready(self) -> None: ...
    def append(
        self, completed: CompletedResolvedPrefixSnapshot, content: bytes
    ) -> ArchivedResolvedPrefix: ...
    def load(self, scope: StateScope, execution_digest: str) -> ArchivedResolvedPrefix: ...
    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ResolvedExecutionHistoryPage: ...
    def content(self, scope: StateScope, execution_digest: str) -> bytes: ...
