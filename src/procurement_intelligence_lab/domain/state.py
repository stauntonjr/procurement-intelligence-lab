"""Canonical operational projection derived from resolved source data."""

from dataclasses import dataclass
from decimal import Decimal

from procurement_intelligence_lab.domain.bom import Bom
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)


@dataclass(frozen=True)
class OperationalBomLine:
    canonical_key: str
    quantity: Decimal
    unit_price: Decimal | None
    source_artifact: str


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
            )
        )
    return tuple(projected)
