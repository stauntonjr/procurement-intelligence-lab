"""Governed expected and observed procurement-state projections."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.domain.bom import Bom, EvidenceRef
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)


class StateFreshness(StrEnum):
    CURRENT = "current"
    PARTIAL = "partial"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StateScope:
    """The tenant/project/site/BOM-revision boundary of a state projection."""

    tenant_id: str
    project_id: str
    site_id: str
    bom_revision: str

    def __post_init__(self) -> None:
        if not all((self.tenant_id, self.project_id, self.site_id, self.bom_revision)):
            raise ValueError("state scope identifiers are required")


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
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")


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
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")


@dataclass(frozen=True)
class ExpectedObservedState:
    expected: ExpectedRequirement
    observed: ObservedProcurement | None

    @property
    def outstanding_quantity(self) -> Decimal:
        received = self.observed.received_quantity if self.observed is not None else Decimal(0)
        return max(self.expected.required_quantity - received, Decimal(0))

    @property
    def freshness(self) -> StateFreshness:
        return self.observed.freshness if self.observed is not None else StateFreshness.UNKNOWN


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
    observed_by_key = {
        item.canonical_key: item for item in observed if item.as_of <= as_of
    }
    return tuple(
        ExpectedObservedState(item, observed_by_key.get(item.canonical_key))
        for item in expected
        if item.as_of <= as_of
    )
