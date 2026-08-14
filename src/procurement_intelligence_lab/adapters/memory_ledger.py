"""In-memory append-only assertion ledger adapter."""

from datetime import datetime

from procurement_intelligence_lab.domain.assertions import SourceAssertion
from procurement_intelligence_lab.domain.ledger import AssertionLedgerEntry


class InMemoryAssertionLedger:
    def __init__(self) -> None:
        self._entries: list[AssertionLedgerEntry] = []

    def append(
        self, assertion: SourceAssertion, *, observed_at: datetime
    ) -> AssertionLedgerEntry:
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        entry = AssertionLedgerEntry(len(self._entries) + 1, assertion, observed_at)
        self._entries.append(entry)
        return entry

    def entries(self) -> tuple[AssertionLedgerEntry, ...]:
        return tuple(self._entries)

    def as_of(self, observed_at: datetime) -> tuple[AssertionLedgerEntry, ...]:
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return tuple(entry for entry in self._entries if entry.observed_at <= observed_at)
