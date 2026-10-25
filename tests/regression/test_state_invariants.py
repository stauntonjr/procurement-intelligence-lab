from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone, tzinfo
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
    compare_expected_observed,
    expected_requirements,
)
from procurement_intelligence_lab.platform.semantics.errors import TemporalContractError

EVIDENCE = (EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A",)),)
SCOPE = StateScope("tenant", "project", "site", "v1")
AS_OF = datetime(2026, 1, 1, tzinfo=UTC)
QUANTITY_FIELDS = (
    "required_quantity",
    "ordered_quantity",
    "received_quantity",
    "substituted_quantity",
    "delayed_quantity",
    "unknown_quantity",
)


def _observed() -> ObservedProcurement:
    return ObservedProcurement(
        "GPU-A",
        Decimal(4),
        Decimal(3),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        SCOPE,
        AS_OF,
        StateFreshness.PARTIAL,
        EVIDENCE,
    )


def _quantity_record(field: str, quantity: Decimal) -> ExpectedRequirement | ObservedProcurement:
    if field == "required_quantity":
        return ExpectedRequirement("GPU-A", quantity, SCOPE, AS_OF, EVIDENCE)
    return replace(_observed(), **{field: quantity})


@pytest.mark.regression
@pytest.mark.parametrize("field", QUANTITY_FIELDS)
@pytest.mark.parametrize(
    "quantity", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")]
)
def test_every_quantity_rejects_nonfinite_values(field: str, quantity: Decimal) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        _quantity_record(field, quantity)


@pytest.mark.regression
@pytest.mark.parametrize("field", QUANTITY_FIELDS)
@given(st.decimals(allow_nan=False, allow_infinity=False, max_value=-Decimal("0.000001")))
def test_every_quantity_rejects_negative_values(field: str, quantity: Decimal) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        _quantity_record(field, quantity)


@pytest.mark.regression
@pytest.mark.parametrize("field", QUANTITY_FIELDS)
@given(st.decimals(min_value=0, max_value=Decimal("1e12"), places=4))
def test_nonnegative_components_remain_representable(field: str, quantity: Decimal) -> None:
    record = _quantity_record(field, quantity)
    assert getattr(record, field) == quantity
    assert record.evidence == EVIDENCE and record.scope == SCOPE and record.as_of == AS_OF


@pytest.mark.regression
@pytest.mark.parametrize("field", QUANTITY_FIELDS)
@pytest.mark.parametrize("quantity", [Decimal(0), Decimal("0.125"), Decimal("1e100")])
def test_zero_fractional_and_large_components_preserve_exact_values(
    field: str, quantity: Decimal
) -> None:
    assert getattr(_quantity_record(field, quantity), field) == quantity


@pytest.mark.regression
@pytest.mark.parametrize("observed", [False, True])
def test_material_records_require_evidence(observed: bool) -> None:
    record = (
        _observed()
        if observed
        else ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, EVIDENCE)
    )
    with pytest.raises(ValueError, match="requires evidence"):
        replace(record, evidence=())


@pytest.mark.regression
@pytest.mark.parametrize("axis", ["tenant_id", "project_id", "site_id", "version"])
def test_expected_observed_pair_checks_every_scope_axis(axis: str) -> None:
    expected = ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, EVIDENCE)
    observed = replace(_observed(), scope=replace(SCOPE, **{axis: "other"}))
    with pytest.raises(ValueError, match="scopes must match"):
        ExpectedObservedState(expected, observed)


@pytest.mark.regression
def test_missing_partial_and_overage_observations_keep_their_meaning() -> None:
    expected = ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, EVIDENCE)
    missing = ExpectedObservedState(expected, None)
    assert missing.observed is None and missing.freshness is StateFreshness.UNKNOWN
    partial = ExpectedObservedState(expected, _observed())
    assert (
        partial.outstanding_quantity == Decimal(1) and partial.freshness is StateFreshness.PARTIAL
    )
    overage = replace(_observed(), received_quantity=Decimal("5.25"), delayed_quantity=Decimal(9))
    pair = ExpectedObservedState(expected, overage)
    assert pair.observed == overage and pair.outstanding_quantity == Decimal(0)


class _OffsetlessTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None


def _invoke_boundary(boundary: str, as_of: datetime) -> object:
    if boundary == "expected":
        return ExpectedRequirement("GPU-A", Decimal(4), SCOPE, as_of, EVIDENCE)
    if boundary == "observed":
        return replace(_observed(), as_of=as_of)
    if boundary == "project":
        return expected_requirements((), scope=SCOPE, as_of=as_of)
    assert boundary == "compare"
    return compare_expected_observed((), (), as_of=as_of)


@pytest.mark.regression
@pytest.mark.parametrize("boundary", ["expected", "observed", "project", "compare"])
def test_state_boundaries_reject_offsetless_timezone(boundary: str) -> None:
    as_of = AS_OF.replace(tzinfo=_OffsetlessTimezone())
    assert as_of.tzinfo is not None and as_of.utcoffset() is None
    with pytest.raises(TemporalContractError, match="as_of must be timezone-aware"):
        _invoke_boundary(boundary, as_of)


@pytest.mark.regression
@pytest.mark.parametrize("boundary", ["expected", "observed", "project", "compare"])
def test_state_boundaries_reject_naive_time_even_for_empty_inputs(boundary: str) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _invoke_boundary(boundary, AS_OF.replace(tzinfo=None))


@pytest.mark.regression
@given(st.integers(min_value=-1439, max_value=1439))
def test_valid_offsets_and_different_record_times_are_preserved(offset: int) -> None:
    as_of = AS_OF.astimezone(timezone(timedelta(minutes=offset)))
    expected = ExpectedRequirement("GPU-A", Decimal(4), SCOPE, as_of, EVIDENCE)
    observed = replace(_observed(), as_of=as_of + timedelta(hours=1))
    pair = compare_expected_observed((expected,), (observed,), as_of=observed.as_of)[0]
    assert pair.expected.as_of is as_of and pair.observed is observed
    assert expected_requirements((), scope=SCOPE, as_of=as_of) == ()


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
