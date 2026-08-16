"""Evidence-backed Purchase Order records."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_RECEIVED = "partially_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} is required")


def _require_nonnegative(name: str, value: Decimal) -> None:
    if not value.is_finite() or value < Decimal(0):
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class PurchaseOrderLine:
    line_id: str
    item_key: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    currency: str
    required_by: date | None
    evidence: EvidenceRef
    boq_id: str | None = None
    boq_line_id: str | None = None
    boq_scope: StateScope | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("line_id", self.line_id),
            ("item_key", self.item_key),
            ("unit", self.unit),
        ):
            _require_text(name, value)
        _require_nonnegative("quantity", self.quantity)
        _require_nonnegative("unit_price", self.unit_price)
        if (
            len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("currency must be an uppercase ISO-style three-letter code")
        boq_reference = (self.boq_id, self.boq_line_id, self.boq_scope)
        if any(value is not None for value in boq_reference) and any(
            value is None for value in boq_reference
        ):
            raise ValueError("BoQ document, line, and scope references must be supplied together")

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_price

    @property
    def purchase_order_line_id(self) -> str:
        return stable_id(
            "purchase-order-line",
            self.line_id,
            self.item_key,
            str(self.quantity),
            self.unit,
            str(self.unit_price),
            self.currency,
            self.required_by.isoformat() if self.required_by else None,
            self.evidence.evidence_id,
            self.boq_id,
            self.boq_line_id,
        )


@dataclass(frozen=True)
class PurchaseOrder:
    order_number: str
    supplier_key: str
    scope: StateScope
    issued_at: datetime
    status: PurchaseOrderStatus
    lines: tuple[PurchaseOrderLine, ...]
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        _require_text("order_number", self.order_number)
        _require_text("supplier_key", self.supplier_key)
        if self.issued_at.tzinfo is None:
            raise ValueError("purchase-order issued_at must be timezone-aware")
        if not self.lines:
            raise ValueError("purchase order requires at least one line")
        line_ids = tuple(line.line_id for line in self.lines)
        if len(set(line_ids)) != len(line_ids):
            raise ValueError("purchase-order line IDs must be unique")
        if any(line.boq_scope is not None and line.boq_scope != self.scope for line in self.lines):
            raise ValueError("purchase-order and referenced BoQ line scope must match")

    @property
    def total(self) -> Decimal:
        return sum((line.total for line in self.lines), Decimal(0))

    @property
    def purchase_order_id(self) -> str:
        return stable_id(
            "purchase-order",
            self.order_number,
            self.supplier_key,
            self.scope.tenant_id,
            self.scope.project_id,
            self.scope.site_id,
            self.scope.version,
            tuple(line.purchase_order_line_id for line in self.lines),
            self.evidence.evidence_id,
        )
