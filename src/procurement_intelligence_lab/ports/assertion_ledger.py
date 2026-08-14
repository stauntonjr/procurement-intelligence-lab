"""Outbound persistence ports."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.domain.assertions import SourceAssertion
from procurement_intelligence_lab.domain.ledger import AssertionLedgerEntry


class AssertionLedger(Protocol):
    """Append-only storage contract for source assertions."""

    def append(
        self, assertion: SourceAssertion, *, observed_at: datetime
    ) -> AssertionLedgerEntry: ...

    def entries(self) -> tuple[AssertionLedgerEntry, ...]: ...

    def as_of(self, observed_at: datetime) -> tuple[AssertionLedgerEntry, ...]: ...
