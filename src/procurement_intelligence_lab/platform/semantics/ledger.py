"""Append-only source-assertion ledger records."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.identity import stable_id


@dataclass(frozen=True)
class AssertionLedgerEntry:
    sequence: int
    assertion: SourceAssertion
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("ledger sequence must be positive")
        if self.observed_at.tzinfo is None:
            raise ValueError("ledger observation time must be timezone-aware")

    @property
    def entry_id(self) -> str:
        return stable_id(
            "assertion-entry",
            self.sequence,
            self.assertion.assertion_id,
            self.observed_at.isoformat(),
        )
