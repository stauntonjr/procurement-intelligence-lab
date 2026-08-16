"""Evidence-backed Bill of Quantities records."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} is required")


def _require_nonnegative(name: str, value: Decimal) -> None:
    if not value.is_finite() or value < Decimal(0):
        raise ValueError(f"{name} must be a finite non-negative quantity")


@dataclass(frozen=True)
class BoqLine:
    line_id: str
    item_key: str
    description: str
    quantity: Decimal
    unit: str
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        for name, value in (
            ("line_id", self.line_id),
            ("item_key", self.item_key),
            ("description", self.description),
            ("unit", self.unit),
        ):
            _require_text(name, value)
        _require_nonnegative("quantity", self.quantity)

    @property
    def boq_line_id(self) -> str:
        return stable_id(
            "boq-line",
            self.line_id,
            self.item_key,
            str(self.quantity),
            self.unit,
            self.evidence.evidence_id,
        )


@dataclass(frozen=True)
class Boq:
    boq_number: str
    revision: str
    scope: StateScope
    as_of: datetime
    evidence: EvidenceRef
    lines: tuple[BoqLine, ...]

    def __post_init__(self) -> None:
        _require_text("boq_number", self.boq_number)
        _require_text("revision", self.revision)
        if self.scope.version != self.revision:
            raise ValueError("BoQ revision must match its state scope version")
        if self.as_of.tzinfo is None:
            raise ValueError("BoQ as_of must be timezone-aware")
        if not self.lines:
            raise ValueError("BoQ requires at least one line")
        line_ids = tuple(line.line_id for line in self.lines)
        if len(set(line_ids)) != len(line_ids):
            raise ValueError("BoQ line IDs must be unique")

    @property
    def boq_id(self) -> str:
        return stable_id(
            "boq",
            self.boq_number,
            self.revision,
            self.scope.tenant_id,
            self.scope.project_id,
            self.scope.site_id,
            self.evidence.evidence_id,
            tuple(line.boq_line_id for line in self.lines),
        )
