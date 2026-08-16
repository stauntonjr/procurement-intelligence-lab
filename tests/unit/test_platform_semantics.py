from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

import pytest

from procurement_intelligence_lab.platform.semantics.anomalies import (
    Anomaly,
    AnomalySeverity,
    AnomalyStatus,
)
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.evidence import (
    EvidenceBackedResult,
    EvidenceRef,
    RecordLocation,
    TabularLocation,
)
from procurement_intelligence_lab.platform.semantics.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)
from procurement_intelligence_lab.platform.semantics.reconciliation import SourcePrecedencePolicy
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class InventoryPredicate(StrEnum):
    HAS_COUNT = "has_count"


class InventoryAnomalyKind(StrEnum):
    COUNT_MISMATCH = "count_mismatch"


@dataclass(frozen=True)
class InventoryCountMismatch:
    expected: int
    observed: int

    @property
    def kind(self) -> InventoryAnomalyKind:
        return InventoryAnomalyKind.COUNT_MISMATCH


@dataclass(frozen=True)
class InventoryObservation:
    source_artifact: str


@dataclass(frozen=True)
class JsonPointerLocation:
    pointer: str

    @property
    def location_kind(self) -> str:
        return "json_pointer"

    def identity_parts(self) -> tuple[object, ...]:
        return (self.location_kind, self.pointer)

    def payload_fields(self) -> dict[str, object]:
        return {"pointer": self.pointer}


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        ProvenanceContext(
            "inventory-run",
            "inventory-count",
            "1",
            "revision",
            "image",
            "config",
            None,
            ("snapshot",),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        "inventory-counter",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def test_typed_tabular_location_preserves_legacy_evidence_identity() -> None:
    legacy = EvidenceRef("inventory.xlsx", "hash", "Counts", 2, ("A", "B"))
    typed = EvidenceRef(
        "inventory.xlsx",
        "hash",
        TabularLocation("Counts", 2, ("A", "B")),
    )

    assert typed.evidence_id == legacy.evidence_id
    assert typed.as_dict()["location_kind"] == "tabular"


def test_non_procurement_vertical_uses_shared_evidence_ledger_and_anomaly_contracts() -> None:
    evidence = EvidenceRef("inventory-api", "hash", RecordLocation("counts", "rack-7"))
    assertion = SourceAssertion("rack-7", InventoryPredicate.HAS_COUNT, Decimal(4), evidence)
    entry = AssertionLedgerEntry(1, assertion, datetime(2026, 1, 1, tzinfo=UTC))
    result = EvidenceBackedResult(Decimal(4), (evidence,), EpistemicStatus.OBSERVED)
    anomaly = Anomaly(
        "rack-7",
        InventoryCountMismatch(4, 3),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        (evidence,),
        "inventory-count-v1",
        _provenance(),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateScope("tenant", "inventory", "warehouse", "snapshot-v1"),
    )

    assert entry.assertion.assertion_id
    assert result.value == Decimal(4)
    assert anomaly.kind is InventoryAnomalyKind.COUNT_MISMATCH
    assert anomaly.expected == 4


def test_source_precedence_policy_is_vertical_neutral_and_fail_closed() -> None:
    policy = SourcePrecedencePolicy(("cycle-count", "erp"))

    assert (
        policy.governing_source((InventoryObservation("erp"), InventoryObservation("cycle-count")))
        == "cycle-count"
    )
    with pytest.raises(ValueError, match="no source-precedence"):
        policy.governing_source((InventoryObservation("unregistered"),))


@pytest.mark.parametrize(
    "location",
    [
        lambda: TabularLocation("", 1, ("A",)),
        lambda: TabularLocation("Sheet", 0, ("A",)),
        lambda: RecordLocation("counts", ""),
    ],
)
def test_evidence_locations_fail_closed(location: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        location()


def test_evidence_reference_rejects_incomplete_or_mixed_locator_forms() -> None:
    with pytest.raises(ValueError, match="artifact ID"):
        EvidenceRef("", "hash", RecordLocation("counts", "rack-7"))
    with pytest.raises(ValueError, match="row and cells"):
        EvidenceRef("inventory.xlsx", "hash", "Counts")
    with pytest.raises(ValueError, match="cannot be combined"):
        EvidenceRef(
            "inventory.xlsx",
            "hash",
            RecordLocation("counts", "rack-7"),
            row=2,
        )
    with pytest.raises(TypeError, match="EvidenceLocation"):
        EvidenceRef("inventory.xlsx", "hash", object())


def test_record_evidence_has_typed_payload_and_rejects_tabular_accessors() -> None:
    evidence = EvidenceRef("inventory-api", "hash", RecordLocation("counts", "rack-7"))

    assert evidence.as_dict()["collection"] == "counts"
    for accessor in (lambda: evidence.sheet, lambda: evidence.row, lambda: evidence.cells):
        with pytest.raises(TypeError, match="tabular"):
            accessor()


def test_custom_evidence_location_extends_identity_and_public_payload() -> None:
    evidence = EvidenceRef("inventory.json", "hash", JsonPointerLocation("/racks/7/count"))

    assert evidence.as_dict()["pointer"] == "/racks/7/count"
    assert evidence.as_dict()["location_kind"] == "json_pointer"


def test_unresolved_evidence_result_cannot_carry_a_value() -> None:
    with pytest.raises(ValueError, match="unresolved"):
        EvidenceBackedResult(Decimal(4), (), EpistemicStatus.UNRESOLVED)
