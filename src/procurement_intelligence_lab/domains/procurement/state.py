"""Governed expected and observed procurement-state projections."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.bom import Bom
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.state import StateFreshness


@dataclass(frozen=True)
class OperationalBomLine:
    canonical_key: str
    quantity: Decimal
    unit_price: Decimal | None
    source_artifact: str
    evidence: EvidenceRef


@dataclass(frozen=True)
class ExpectedRequirement:
    canonical_key: str
    required_quantity: Decimal
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.canonical_key:
            raise ValueError("canonical_key is required")
        _require_nonnegative("required_quantity", self.required_quantity)
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if not self.evidence:
            raise ValueError("expected state requires evidence")


@dataclass(frozen=True)
class ObservedProcurement:
    canonical_key: str
    ordered_quantity: Decimal
    received_quantity: Decimal
    substituted_quantity: Decimal
    delayed_quantity: Decimal
    unknown_quantity: Decimal
    scope: StateScope
    as_of: datetime
    freshness: StateFreshness
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.canonical_key:
            raise ValueError("canonical_key is required")
        quantities = {
            "ordered_quantity": self.ordered_quantity,
            "received_quantity": self.received_quantity,
            "substituted_quantity": self.substituted_quantity,
            "delayed_quantity": self.delayed_quantity,
            "unknown_quantity": self.unknown_quantity,
        }
        for name, value in quantities.items():
            _require_nonnegative(name, value)
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if not self.evidence:
            raise ValueError("observed state requires evidence")


@dataclass(frozen=True)
class ExpectedObservedState:
    expected: ExpectedRequirement
    observed: ObservedProcurement | None

    def __post_init__(self) -> None:
        if self.observed is None:
            return
        if self.expected.canonical_key != self.observed.canonical_key:
            raise ValueError("expected and observed canonical keys must match")
        if self.expected.scope != self.observed.scope:
            raise ValueError("expected and observed scopes must match")

    @property
    def outstanding_quantity(self) -> Decimal:
        received = self.observed.received_quantity if self.observed is not None else Decimal(0)
        return max(self.expected.required_quantity - received, Decimal(0))

    @property
    def freshness(self) -> StateFreshness:
        return self.observed.freshness if self.observed is not None else StateFreshness.UNKNOWN


def _require_nonnegative(name: str, value: Decimal) -> None:
    if not value.is_finite() or value < Decimal(0):
        raise ValueError(f"{name} must be a finite non-negative quantity")


def project_operational_lines(
    bom: Bom,
    decisions: tuple[ResolutionDecision, ...],
) -> tuple[OperationalBomLine, ...]:
    by_mention = {decision.mention: decision for decision in decisions}
    projected: list[OperationalBomLine] = []
    for line in bom.lines:
        decision = by_mention.get(line.sku)
        if decision is None or decision.status is not ResolutionStatus.RESOLVED:
            continue
        assert decision.canonical_key is not None
        projected.append(
            OperationalBomLine(
                decision.canonical_key,
                line.quantity,
                line.unit_price,
                line.evidence.artifact_id,
                line.evidence,
            )
        )
    return tuple(projected)


def expected_requirements(
    lines: tuple[OperationalBomLine, ...],
    *,
    scope: StateScope,
    as_of: datetime,
) -> tuple[ExpectedRequirement, ...]:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    grouped: dict[str, list[OperationalBomLine]] = {}
    for line in lines:
        grouped.setdefault(line.canonical_key, []).append(line)
    return tuple(
        ExpectedRequirement(
            canonical_key,
            sum((line.quantity for line in group), Decimal(0)),
            scope,
            as_of,
            tuple(line.evidence for line in group),
        )
        for canonical_key, group in sorted(grouped.items())
    )


def compare_expected_observed(
    expected: tuple[ExpectedRequirement, ...],
    observed: tuple[ObservedProcurement, ...],
    *,
    as_of: datetime,
) -> tuple[ExpectedObservedState, ...]:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    observed_by_key: dict[tuple[StateScope, str], ObservedProcurement] = {}
    for item in observed:
        if item.as_of > as_of:
            continue
        key = (item.scope, item.canonical_key)
        current = observed_by_key.get(key)
        if current is None or item.as_of > current.as_of:
            observed_by_key[key] = item

    return tuple(
        ExpectedObservedState(item, observed_by_key.get((item.scope, item.canonical_key)))
        for item in expected
        if item.as_of <= as_of
    )
