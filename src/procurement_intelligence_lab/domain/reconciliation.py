"""Deterministic reconciliation of resolved operational observations."""

from dataclasses import dataclass
from decimal import Decimal

from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.provenance import DecisionProvenance
from procurement_intelligence_lab.domain.state import OperationalBomLine


@dataclass(frozen=True)
class ReconciledLine:
    canonical_key: str
    quantity: Decimal
    unit_price: Decimal | None
    governing_source_artifact: str
    source_artifacts: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]
    losing_evidence: tuple[EvidenceRef, ...]
    status: str
    provenance: DecisionProvenance


class ReconciliationPolicyError(ValueError):
    """Raised when no explicit policy can select a governing observation."""


@dataclass(frozen=True)
class ReconciliationPolicy:
    """Select the first available source in explicit precedence order."""

    source_precedence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_precedence:
            raise ValueError("source_precedence must not be empty")
        if len(set(self.source_precedence)) != len(self.source_precedence):
            raise ValueError("source_precedence must not contain duplicates")

    def governing_source(self, observations: list[OperationalBomLine]) -> str:
        available = {line.source_artifact for line in observations}
        for source in self.source_precedence:
            if source in available:
                return source
        raise ReconciliationPolicyError(
            f"no source-precedence rule covers observations from {sorted(available)!r}"
        )


def reconcile_lines(
    lines: tuple[OperationalBomLine, ...],
    *,
    policy: ReconciliationPolicy,
    provenance: DecisionProvenance,
) -> tuple[ReconciledLine, ...]:
    grouped: dict[str, list[OperationalBomLine]] = {}
    for line in lines:
        grouped.setdefault(line.canonical_key, []).append(line)

    reconciled: list[ReconciledLine] = []
    for key in sorted(grouped):
        observations = grouped[key]
        governing_source = policy.governing_source(observations)
        governing = [line for line in observations if line.source_artifact == governing_source]
        losing = [line for line in observations if line.source_artifact != governing_source]
        prices = {line.unit_price for line in governing}
        unit_price = next(iter(prices)) if len(prices) == 1 else None
        quantity = sum((line.quantity for line in governing), Decimal(0))
        governing_signature = (quantity, unit_price)
        losing_signatures = {
            (
                sum(
                    (line.quantity for line in observations if line.source_artifact == source),
                    Decimal(0),
                ),
                _single_price([line for line in observations if line.source_artifact == source]),
            )
            for source in {line.source_artifact for line in losing}
        }
        status = (
            "conflict"
            if len(prices) != 1 or any(item != governing_signature for item in losing_signatures)
            else "reconciled"
        )
        reconciled.append(
            ReconciledLine(
                key,
                quantity,
                unit_price,
                governing_source,
                tuple(sorted({line.source_artifact for line in observations})),
                tuple(line.evidence for line in governing),
                tuple(line.evidence for line in losing),
                status,
                provenance,
            )
        )
    return tuple(reconciled)


def _single_price(observations: list[OperationalBomLine]) -> Decimal | None:
    prices = {line.unit_price for line in observations}
    return next(iter(prices)) if len(prices) == 1 else None
