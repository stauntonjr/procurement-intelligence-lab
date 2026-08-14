"""Append-only source assertion ledger records."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.domain.assertions import SourceAssertion
from procurement_intelligence_lab.domain.identity import stable_id


@dataclass(frozen=True)
class AssertionLedgerEntry:
    sequence: int
    assertion: SourceAssertion
    observed_at: datetime

    @property
    def entry_id(self) -> str:
        return stable_id(
            "assertion-entry",
            self.sequence,
            self.assertion.assertion_id,
            self.observed_at.isoformat(),
        )
