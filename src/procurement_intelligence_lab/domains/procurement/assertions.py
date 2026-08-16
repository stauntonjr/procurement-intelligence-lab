"""Source assertions retain what a document said before reconciliation."""

from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.domains.procurement.bom import Bom
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef


class AssertionPredicate(StrEnum):
    HAS_SKU = "has_sku"
    HAS_DESCRIPTION = "has_description"
    HAS_QUANTITY = "has_quantity"
    HAS_UNIT_PRICE = "has_unit_price"


def assertions_for_bom_line(
    sku: str,
    description: str,
    quantity: Decimal,
    unit_price: Decimal | None,
    evidence: EvidenceRef,
    transformation_event_id: str | None = None,
) -> tuple[SourceAssertion, ...]:
    assertions = (
        SourceAssertion(
            sku,
            AssertionPredicate.HAS_SKU,
            sku,
            evidence,
            transformation_event_id=transformation_event_id,
        ),
        SourceAssertion(
            sku,
            AssertionPredicate.HAS_DESCRIPTION,
            description,
            evidence,
            transformation_event_id=transformation_event_id,
        ),
        SourceAssertion(
            sku,
            AssertionPredicate.HAS_QUANTITY,
            quantity,
            evidence,
            transformation_event_id=transformation_event_id,
        ),
    )
    if unit_price is None:
        return assertions
    return assertions + (
        SourceAssertion(
            sku,
            AssertionPredicate.HAS_UNIT_PRICE,
            unit_price,
            evidence,
            transformation_event_id=transformation_event_id,
        ),
    )


def assertions_for_bom(
    bom: Bom,
    transformation_event_id: str | None = None,
) -> tuple[SourceAssertion, ...]:
    assertions: list[SourceAssertion] = []
    for line in bom.lines:
        assertions.extend(
            assertions_for_bom_line(
                line.sku,
                line.description,
                line.quantity,
                line.unit_price,
                line.evidence,
                transformation_event_id,
            )
        )
    return tuple(assertions)
