"""Durable job journal and atomic source/archive/attempt publication."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobFailure,
    ResolvedAbandonAttemptCommand,
    ResolvedAttemptToken,
    ResolvedJobDefinition,
    ResolvedJobHistoryPage,
    ResolvedJobJournalReceipt,
    ResolvedJobView,
    ResolvedStartAttemptCommand,
    ResolvedStartClaim,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class ResolvedPrefixJobs(Protocol):
    def check_ready(self) -> None: ...
    def submit(self, job: ResolvedJobDefinition, *, now: datetime) -> ResolvedJobJournalReceipt: ...
    def load(self, scope: StateScope, job_id: str) -> ResolvedJobView: ...
    def lookup_command(
        self, command: ResolvedStartAttemptCommand | ResolvedAbandonAttemptCommand
    ) -> ResolvedJobJournalReceipt | None: ...
    def start(
        self, command: ResolvedStartAttemptCommand, *, now: datetime
    ) -> ResolvedStartClaim: ...
    def abandon(
        self, command: ResolvedAbandonAttemptCommand, *, now: datetime
    ) -> ResolvedJobJournalReceipt: ...
    def fail(
        self, token: ResolvedAttemptToken, failure: JobFailure, *, now: datetime
    ) -> ResolvedJobJournalReceipt: ...
    def complete(
        self,
        token: ResolvedAttemptToken,
        completed: CompletedResolvedPrefixSnapshot,
        content: bytes,
        *,
        now: datetime,
    ) -> ResolvedJobJournalReceipt: ...
    def history(
        self, scope: StateScope, job_id: str, *, limit: int = 100, after_sequence: int = 0
    ) -> ResolvedJobHistoryPage: ...
    def content(self, scope: StateScope, job_id: str) -> bytes: ...
