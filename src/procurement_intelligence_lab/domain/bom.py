"""Evidence-preserving BOM domain objects and deterministic queries."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EpistemicStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class EvidenceRef:
    artifact_id: str
    content_hash: str
    sheet: str
    row: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class BomLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal | None
    evidence: EvidenceRef
    status: EpistemicStatus = EpistemicStatus.OBSERVED


@dataclass(frozen=True)
class Bom:
    artifact_id: str
    lines: tuple[BomLine, ...]


@dataclass(frozen=True)
class QueryResult:
    value: object
    evidence: tuple[EvidenceRef, ...]
    status: EpistemicStatus


def distinct_skus(bom: Bom) -> QueryResult:
    lines = tuple(line for line in bom.lines if line.status is not EpistemicStatus.UNRESOLVED)
    return QueryResult(
        tuple(sorted({line.sku for line in lines})),
        tuple(line.evidence for line in lines),
        EpistemicStatus.OBSERVED,
    )


def gpu_quantity(bom: Bom) -> QueryResult:
    lines = tuple(
        line
        for line in bom.lines
        if "gpu" in line.description.lower() and line.status is not EpistemicStatus.UNRESOLVED
    )
    return QueryResult(
        sum((line.quantity for line in lines), Decimal(0)),
        tuple(line.evidence for line in lines),
        EpistemicStatus.OBSERVED,
    )


def bom_cost(bom: Bom) -> QueryResult:
    lines = tuple(line for line in bom.lines if line.status is not EpistemicStatus.UNRESOLVED)
    evidence = tuple(line.evidence for line in lines)
    if any(line.unit_price is None for line in lines):
        return QueryResult(None, evidence, EpistemicStatus.UNRESOLVED)

    total = Decimal(0)
    for line in lines:
        assert line.unit_price is not None
        total += line.quantity * line.unit_price
    return QueryResult(total, evidence, EpistemicStatus.OBSERVED)
