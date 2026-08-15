from datetime import UTC, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.adapters.memory_ledger import InMemoryAssertionLedger
from procurement_intelligence_lab.domains.procurement.assertions import (
    AssertionPredicate,
    SourceAssertion,
)
from procurement_intelligence_lab.domains.procurement.bom import EvidenceRef


def _assertion(quantity: str) -> SourceAssertion:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    return SourceAssertion("GPU-A", AssertionPredicate.HAS_QUANTITY, Decimal(quantity), evidence)


def test_assertion_ids_are_stable() -> None:
    assert _assertion("4").assertion_id == _assertion("4").assertion_id
    assert _assertion("4").assertion_id != _assertion("8").assertion_id


def test_in_memory_ledger_is_append_only_and_ordered() -> None:
    ledger = InMemoryAssertionLedger()
    first_time = datetime(2026, 1, 1, tzinfo=UTC)
    second_time = datetime(2026, 1, 2, tzinfo=UTC)

    first = ledger.append(_assertion("4"), observed_at=first_time)
    second = ledger.append(_assertion("8"), observed_at=second_time)

    assert [entry.sequence for entry in ledger.entries()] == [1, 2]
    assert first.entry_id != second.entry_id
    assert ledger.as_of(first_time) == (first,)
    assert ledger.as_of(second_time) == (first, second)


def test_ledger_requires_timezone_aware_timestamps() -> None:
    ledger = InMemoryAssertionLedger()

    with pytest.raises(ValueError, match="timezone-aware"):
        ledger.append(_assertion("4"), observed_at=datetime(2026, 1, 1))  # noqa: DTZ001
