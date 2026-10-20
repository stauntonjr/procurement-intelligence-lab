"""BOM review admission; no governing authority or unit reinterpretation."""

import re
from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewProposal
from procurement_intelligence_lab.platform.semantics.errors import ReviewContractError


def validate_bom_review(proposal: ReviewProposal) -> None:
    predicate, value = proposal.previous.predicate, proposal.proposed_value
    context = proposal.previous.context
    if type(predicate) is not AssertionPredicate or context is None:
        raise ReviewContractError("review requires the BOM assertion profile")
    observation = context.observation
    expected_names = {
        AssertionPredicate.HAS_SKU: "sku",
        AssertionPredicate.HAS_DESCRIPTION: "description",
        AssertionPredicate.HAS_QUANTITY: "quantity",
        AssertionPredicate.HAS_UNIT_PRICE: "unit_price",
    }
    name = expected_names.get(predicate)
    if (
        name is None
        or observation.source_field.field_name != name
        or observation.predicate != f"procurement.bom.{name}"
    ):
        raise ReviewContractError("review source predicate must match its BOM observation")
    if (
        (predicate is AssertionPredicate.HAS_QUANTITY and observation.unit != "each")
        or (
            predicate is AssertionPredicate.HAS_UNIT_PRICE
            and (
                observation.unit is None
                or re.fullmatch(r"[A-Z]{3}/(each|dozen)", observation.unit) is None
            )
        )
        or (
            predicate in (AssertionPredicate.HAS_SKU, AssertionPredicate.HAS_DESCRIPTION)
            and observation.unit is not None
        )
    ):
        raise ReviewContractError("review must preserve a supported declared source unit")
    if predicate in (AssertionPredicate.HAS_QUANTITY, AssertionPredicate.HAS_UNIT_PRICE):
        if any(v is not None and type(v) is not Decimal for v in (value, proposal.previous.value)):
            raise ReviewContractError("BOM numeric review requires exact Decimal or explicit null")
    elif predicate in (AssertionPredicate.HAS_SKU, AssertionPredicate.HAS_DESCRIPTION):
        if value is not None and (type(value) is not str or not value.strip()):
            raise ReviewContractError("BOM text review requires nonblank text or explicit null")
    else:
        raise ReviewContractError(
            "unmapped or unsupported predicates require a separate mapping workflow"
        )
