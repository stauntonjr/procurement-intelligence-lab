"""Durable job journal and atomic source/archive/attempt publication."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    AttemptToken,
    JobDefinition,
    JobFailure,
    JobHistoryPage,
    JobJournalReceipt,
    JobView,
    StartAttemptCommand,
    StartClaim,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class LocalPrefixJobs(Protocol):
    def check_ready(self) -> None: ...
    def submit(self, job: JobDefinition, *, now: datetime) -> JobJournalReceipt: ...
    def load(self, scope: StateScope, job_id: str) -> JobView: ...
    def lookup_command(
        self, command: StartAttemptCommand | AbandonAttemptCommand
    ) -> JobJournalReceipt | None: ...
    def start(self, command: StartAttemptCommand, *, now: datetime) -> StartClaim: ...
    def abandon(self, command: AbandonAttemptCommand, *, now: datetime) -> JobJournalReceipt: ...
    def fail(
        self, token: AttemptToken, failure: JobFailure, *, now: datetime
    ) -> JobJournalReceipt: ...
    def complete(
        self,
        token: AttemptToken,
        completed: CompletedPrefixSnapshot,
        content: bytes,
        *,
        now: datetime,
    ) -> JobJournalReceipt: ...
    def history(
        self, scope: StateScope, job_id: str, *, limit: int = 100, after_sequence: int = 0
    ) -> JobHistoryPage: ...
    def content(self, scope: StateScope, job_id: str) -> bytes: ...
