from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimStatus,
    GoverningPredicate,
    GoverningSourceType,
    reconcile_claims,
    reconcile_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)

AS_OF = datetime(2026, 1, 15, tzinfo=UTC)
SCOPE = StateScope("tenant", "project", "site", "revision-independent")
CONTEXT = RequestContext(
    "planner", "tenant", "project", "site", frozenset({Permission.READ_STATE}), "trace"
)


def _claim(
    revision: str,
    quantity: str,
    *,
    approved_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC),
    effective_from: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    effective_until: datetime | None = None,
    supersedes: tuple[str, ...] = (),
) -> GoverningClaim:
    return GoverningClaim(
        claim_id=f"claim:{revision}",
        canonical_key="GPU-A",
        predicate=GoverningPredicate.REQUIRED_QUANTITY,
        value=Decimal(quantity),
        unit="each",
        source_type=GoverningSourceType.APPROVED_BOM_REVISION,
        scope=SCOPE,
        evidence=EvidenceRef(f"{revision}.xlsx", "fixture-hash", "BOM", 2, ("C",)),
        revision_id=revision,
        supersedes_revision_ids=supersedes,
        approved_at=approved_at,
        effective_from=effective_from,
        effective_until=effective_until,
        document_at=datetime(2025, 12, 31, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


@pytest.mark.contract
def test_equal_competing_approved_revisions_govern_a_shared_required_quantity() -> None:
    decision = reconcile_required_quantity(
        (_claim("A", "4"), _claim("B", "4")),
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.GOVERNED_SHARED_VALUE
    assert decision.value == Decimal(4)
    assert decision.unit == "each"
    assert tuple(claim.revision_id for claim in decision.governing) == ("A", "B")
    assert decision.losing == ()
    assert dict(decision.dispositions) == {"claim:A": "governing", "claim:B": "governing"}
    assert decision.policy_id == "procurement-governing-claims/v1"


@pytest.mark.contract
def test_conflicting_competing_approved_revisions_abstain_and_retain_both() -> None:
    decision = reconcile_required_quantity(
        (_claim("A", "4"), _claim("B", "6")),
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.UNRESOLVED
    assert decision.value is None
    assert decision.governing == ()
    assert tuple(claim.revision_id for claim in decision.losing) == ("A", "B")
    assert set(dict(decision.dispositions).values()) == {"conflicting: no value established"}


@pytest.mark.contract
def test_explicit_supersession_and_effectivity_select_one_revision() -> None:
    decision = reconcile_required_quantity(
        (
            _claim("A", "4"),
            _claim("B", "6", supersedes=("A",), effective_from=datetime(2026, 1, 10, tzinfo=UTC)),
        ),
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.GOVERNED
    assert decision.value == Decimal(6)
    assert tuple(claim.revision_id for claim in decision.governing) == ("B",)
    assert tuple(claim.revision_id for claim in decision.losing) == ("A",)


@pytest.mark.contract
def test_missing_approval_or_future_effectivity_cannot_govern() -> None:
    decision = reconcile_required_quantity(
        (
            _claim("A", "4", approved_at=None),
            _claim("B", "6", effective_from=datetime(2026, 2, 1, tzinfo=UTC)),
        ),
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.UNRESOLVED
    assert decision.value is None
    assert tuple(claim.revision_id for claim in decision.losing) == ("A", "B")


@pytest.mark.contract
def test_ordered_quantity_sums_distinct_approved_purchase_order_lines() -> None:
    first = _claim("PO-1", "2")
    second = _claim("PO-2", "3")
    first = replace(
        first,
        predicate=GoverningPredicate.ORDERED_QUANTITY,
        source_type=GoverningSourceType.APPROVED_PURCHASE_ORDER_LINE,
    )
    second = replace(
        second,
        predicate=GoverningPredicate.ORDERED_QUANTITY,
        source_type=GoverningSourceType.APPROVED_PURCHASE_ORDER_LINE,
    )

    decision = reconcile_claims(
        (first, second),
        predicate=GoverningPredicate.ORDERED_QUANTITY,
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.GOVERNED
    assert decision.value == Decimal(5)
    assert tuple(claim.revision_id for claim in decision.governing) == ("PO-1", "PO-2")


@pytest.mark.contract
def test_incompatible_accepted_quotes_abstain_instead_of_selecting_by_document_order() -> None:
    quote_a = _claim("Q-A", "100")
    quote_b = _claim("Q-B", "110")
    quote_a = replace(
        quote_a,
        predicate=GoverningPredicate.PLANNED_UNIT_PRICE,
        source_type=GoverningSourceType.ACCEPTED_SUPPLIER_QUOTE,
        unit="USD",
    )
    quote_b = replace(
        quote_b,
        predicate=GoverningPredicate.PLANNED_UNIT_PRICE,
        source_type=GoverningSourceType.ACCEPTED_SUPPLIER_QUOTE,
        unit="USD",
    )

    decision = reconcile_claims(
        (quote_b, quote_a),
        predicate=GoverningPredicate.PLANNED_UNIT_PRICE,
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert decision.status is GoverningClaimStatus.UNRESOLVED
    assert decision.value is None
    assert tuple(claim.revision_id for claim in decision.losing) == ("Q-A", "Q-B")


@pytest.mark.contract
def test_supplier_commitment_uses_a_temporal_value_and_observed_delivery_requires_event_time() -> (
    None
):
    commitment = replace(
        _claim("COMMITMENT", "0"),
        predicate=GoverningPredicate.EXPECTED_DELIVERY,
        value=datetime(2026, 2, 1, tzinfo=UTC),
        unit="timestamp",
        source_type=GoverningSourceType.SUPPLIER_CONFIRMED_COMMITMENT,
    )
    expected = reconcile_claims(
        (commitment,),
        predicate=GoverningPredicate.EXPECTED_DELIVERY,
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )
    receipt = replace(
        _claim("RECEIPT", "2"),
        predicate=GoverningPredicate.OBSERVED_DELIVERY,
        source_type=GoverningSourceType.RECEIPT,
        observed_at=datetime(2026, 1, 12, tzinfo=UTC),
    )
    observed = reconcile_claims(
        (receipt,),
        predicate=GoverningPredicate.OBSERVED_DELIVERY,
        canonical_key="GPU-A",
        request_context=CONTEXT,
        as_of=AS_OF,
    )

    assert expected.value == datetime(2026, 2, 1, tzinfo=UTC)
    assert expected.status is GoverningClaimStatus.GOVERNED
    assert observed.value == Decimal(2)
    assert observed.status is GoverningClaimStatus.GOVERNED
