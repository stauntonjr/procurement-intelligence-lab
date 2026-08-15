from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from procurement_intelligence_lab.domains.procurement.bom import EvidenceRef
from procurement_intelligence_lab.domains.procurement.state import (
    ExpectedObservedState,
    ExpectedRequirement,
    ObservedProcurement,
    StateFreshness,
    StateScope,
)

EVIDENCE = (EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A",)),)
SCOPE = StateScope("tenant", "project", "site", "v1")
AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.regression
@given(st.decimals(allow_nan=False, allow_infinity=False, max_value=-Decimal("0.001")))
def test_expected_quantity_rejects_every_negative_finite_value(quantity: Decimal) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ExpectedRequirement("GPU-A", quantity, SCOPE, AS_OF, EVIDENCE)


@pytest.mark.regression
@given(st.decimals(allow_nan=False, allow_infinity=False, max_value=-Decimal("0.001")))
def test_observed_quantities_reject_every_negative_finite_value(quantity: Decimal) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ObservedProcurement(
            "GPU-A",
            quantity,
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            SCOPE,
            AS_OF,
            StateFreshness.PARTIAL,
            EVIDENCE,
        )


@pytest.mark.regression
def test_over_receipt_is_preserved_for_anomaly_policy_instead_of_rejected() -> None:
    observed = ObservedProcurement(
        "GPU-A",
        Decimal(4),
        Decimal(5),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        SCOPE,
        AS_OF,
        StateFreshness.CURRENT,
        EVIDENCE,
    )
    assert observed.received_quantity == Decimal(5)


@pytest.mark.regression
def test_expected_observed_pair_rejects_key_and_scope_mismatch() -> None:
    expected = ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, EVIDENCE)
    observed = ObservedProcurement(
        "CPU-A",
        Decimal(4),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        SCOPE,
        AS_OF,
        StateFreshness.CURRENT,
        EVIDENCE,
    )
    with pytest.raises(ValueError, match="canonical keys"):
        ExpectedObservedState(expected, observed)
