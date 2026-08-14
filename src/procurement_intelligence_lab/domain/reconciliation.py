"""Deterministic reconciliation of resolved operational observations."""

from dataclasses import dataclass
from decimal import Decimal

from procurement_intelligence_lab.domain.provenance import DecisionProvenance
from procurement_intelligence_lab.domain.state import OperationalBomLine


@dataclass(frozen=True)
class ReconciledLine:
    canonical_key: str
    quantity: Decimal
    unit_price: Decimal | None
    source_artifacts: tuple[str, ...]
    status: str
    provenance: DecisionProvenance


def reconcile_lines(
    lines: tuple[OperationalBomLine, ...],
    *,
    provenance: DecisionProvenance,
) -> tuple[ReconciledLine, ...]:
    grouped: dict[str, list[OperationalBomLine]] = {}
    for line in lines:
        grouped.setdefault(line.canonical_key, []).append(line)

    reconciled: list[ReconciledLine] = []
    for key in sorted(grouped):
        observations = grouped[key]
        prices = {line.unit_price for line in observations}
        unit_price = next(iter(prices)) if len(prices) == 1 else None
        reconciled.append(
            ReconciledLine(
                key,
                sum((line.quantity for line in observations), Decimal(0)),
                unit_price,
                tuple(sorted({line.source_artifact for line in observations})),
                "reconciled" if len(prices) == 1 else "conflict",
                provenance,
            )
        )
    return tuple(reconciled)
