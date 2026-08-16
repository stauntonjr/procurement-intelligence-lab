from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from procurement_intelligence_lab.domains.procurement.boq import Boq, BoqLine
from procurement_intelligence_lab.domains.procurement.po import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from procurement_intelligence_lab.platform.semantics.evidence import (
    EvidenceRef,
    TabularLocation,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def _evidence(row: int = 2) -> EvidenceRef:
    return EvidenceRef(
        "procurement.xlsx",
        "sha256:fixture",
        TabularLocation("Sheet1", row, ("A", "B", "C")),
    )


def _scope(revision: str = "r1") -> StateScope:
    return StateScope("tenant", "project", "site", revision)


def test_boq_and_purchase_order_retain_scope_revision_and_evidence() -> None:
    boq = Boq(
        "boq-1",
        "r1",
        _scope(),
        datetime(2026, 1, 1, tzinfo=UTC),
        _evidence(),
        (BoqLine("line-1", "gpu", "GPU accelerator", Decimal("2.5"), "each", _evidence()),),
    )
    order = PurchaseOrder(
        "PO-1",
        "supplier-1",
        _scope(),
        datetime(2026, 1, 2, tzinfo=UTC),
        PurchaseOrderStatus.ISSUED,
        (
            PurchaseOrderLine(
                "po-line-1",
                "gpu",
                Decimal("2.5"),
                "each",
                Decimal("100.25"),
                "USD",
                date(2026, 2, 1),
                _evidence(3),
                boq_id=boq.boq_id,
                boq_line_id=boq.lines[0].boq_line_id,
                boq_scope=_scope(),
            ),
        ),
        _evidence(3),
    )

    assert boq.lines[0].quantity == Decimal("2.5")
    assert order.lines[0].boq_id == boq.boq_id
    assert order.lines[0].boq_line_id == boq.lines[0].boq_line_id
    assert order.total == Decimal("250.625")
    assert boq.scope == order.scope
    assert boq.boq_id != order.purchase_order_id


@pytest.mark.parametrize("quantity", [Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_document_lines_reject_invalid_quantities(quantity: Decimal) -> None:
    with pytest.raises(ValueError, match="quantity"):
        BoqLine("line-1", "gpu", "GPU", quantity, "each", _evidence())


def test_purchase_order_rejects_scope_or_revision_mismatch() -> None:
    with pytest.raises(ValueError, match="scope"):
        PurchaseOrder(
            "PO-1",
            "supplier-1",
            _scope("r2"),
            datetime(2026, 1, 2, tzinfo=UTC),
            PurchaseOrderStatus.ISSUED,
            (
                PurchaseOrderLine(
                    "po-line-1",
                    "gpu",
                    Decimal(1),
                    "each",
                    Decimal(100),
                    "USD",
                    None,
                    _evidence(),
                    boq_id="boq-id",
                    boq_line_id="line-1",
                    boq_scope=_scope("r1"),
                ),
            ),
            _evidence(),
        )


@given(
    quantity=st.decimals(min_value=0, max_value=1_000_000, places=4, allow_nan=False),
    price=st.decimals(min_value=0, max_value=1_000_000, places=4, allow_nan=False),
)
def test_purchase_order_line_total_is_exact_decimal_product(
    quantity: Decimal,
    price: Decimal,
) -> None:
    line = PurchaseOrderLine(
        "po-line-1",
        "gpu",
        quantity,
        "each",
        price,
        "USD",
        None,
        _evidence(),
    )

    assert line.total == quantity * price


def test_boq_rejects_invalid_header_time_and_duplicate_lines() -> None:
    line = BoqLine("line-1", "gpu", "GPU", Decimal(1), "each", _evidence())

    with pytest.raises(ValueError, match="boq_number"):
        Boq(" ", "r1", _scope(), datetime(2026, 1, 1, tzinfo=UTC), _evidence(), (line,))
    with pytest.raises(ValueError, match="revision"):
        Boq("boq-1", "r2", _scope(), datetime(2026, 1, 1, tzinfo=UTC), _evidence(), (line,))
    with pytest.raises(ValueError, match="timezone-aware"):
        Boq("boq-1", "r1", _scope(), datetime(2026, 1, 1), _evidence(), (line,))  # noqa: DTZ001
    with pytest.raises(ValueError, match="at least one"):
        Boq("boq-1", "r1", _scope(), datetime(2026, 1, 1, tzinfo=UTC), _evidence(), ())
    with pytest.raises(ValueError, match="unique"):
        Boq(
            "boq-1",
            "r1",
            _scope(),
            datetime(2026, 1, 1, tzinfo=UTC),
            _evidence(),
            (line, line),
        )


@pytest.mark.parametrize("currency", ["usd", "US", "US1", "ÅBC"])
def test_purchase_order_line_rejects_non_iso_style_currency(currency: str) -> None:
    with pytest.raises(ValueError, match="currency"):
        PurchaseOrderLine(
            "po-line-1",
            "gpu",
            Decimal(1),
            "each",
            Decimal(100),
            currency,
            None,
            _evidence(),
        )


def test_purchase_order_line_rejects_partial_boq_reference() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        PurchaseOrderLine(
            "po-line-1",
            "gpu",
            Decimal(1),
            "each",
            Decimal(100),
            "USD",
            None,
            _evidence(),
            boq_line_id="line-id",
        )


def test_purchase_order_rejects_invalid_header_time_and_duplicate_lines() -> None:
    line = PurchaseOrderLine(
        "po-line-1",
        "gpu",
        Decimal(1),
        "each",
        Decimal(100),
        "USD",
        None,
        _evidence(),
    )

    with pytest.raises(ValueError, match="order_number"):
        PurchaseOrder(
            " ",
            "supplier",
            _scope(),
            datetime(2026, 1, 1, tzinfo=UTC),
            PurchaseOrderStatus.DRAFT,
            (line,),
            _evidence(),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        PurchaseOrder(
            "PO-1",
            "supplier",
            _scope(),
            datetime(2026, 1, 1),  # noqa: DTZ001
            PurchaseOrderStatus.DRAFT,
            (line,),
            _evidence(),
        )
    with pytest.raises(ValueError, match="at least one"):
        PurchaseOrder(
            "PO-1",
            "supplier",
            _scope(),
            datetime(2026, 1, 1, tzinfo=UTC),
            PurchaseOrderStatus.DRAFT,
            (),
            _evidence(),
        )
    with pytest.raises(ValueError, match="unique"):
        PurchaseOrder(
            "PO-1",
            "supplier",
            _scope(),
            datetime(2026, 1, 1, tzinfo=UTC),
            PurchaseOrderStatus.DRAFT,
            (line, line),
            _evidence(),
        )
