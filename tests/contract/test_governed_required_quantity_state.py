from datetime import UTC, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_required_quantity,
)
from procurement_intelligence_lab.domains.procurement.state import (
    ObservedProcurement,
    compare_expected_observed,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.platform.semantics.state import StateFreshness


def _context() -> RequestContext:
    return RequestContext(
        "planner",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset({Permission.READ_STATE}),
        "governed-state-test",
    )


@pytest.mark.contract
@pytest.mark.parametrize(
    ("scenario", "expected_quantity", "evidence_count"),
    (
        (ShowcaseScenario.SUPERSEDED, Decimal(6), 1),
        (ShowcaseScenario.SHARED_VALUE, Decimal(4), 2),
    ),
)
def test_governed_required_quantity_projects_expected_state(
    scenario: ShowcaseScenario,
    expected_quantity: Decimal,
    evidence_count: int,
) -> None:
    result = showcase_required_quantity(scenario, request_context=_context())

    assert result.governed_state.expected is not None
    expected = result.governed_state.expected
    assert expected.required_quantity == expected_quantity
    assert expected.as_of == result.as_of
    assert len(expected.evidence) == evidence_count
    assert expected.scope.version.startswith("governed-required-quantity-scope:")


@pytest.mark.contract
@pytest.mark.parametrize("scenario", (ShowcaseScenario.CONFLICT, ShowcaseScenario.MISSING_APPROVAL))
def test_unresolved_required_quantity_never_projects_zero_expected_state(
    scenario: ShowcaseScenario,
) -> None:
    result = showcase_required_quantity(scenario, request_context=_context())

    assert result.governed_state.expected is None
    assert result.governed_state.decision == result.decision


@pytest.mark.contract
def test_governed_expected_state_pairs_with_scoped_observed_state_for_deterministic_arithmetic() -> (
    None
):
    result = showcase_required_quantity(ShowcaseScenario.SHARED_VALUE, request_context=_context())
    assert result.governed_state.expected is not None
    expected = result.governed_state.expected
    observed = ObservedProcurement(
        expected.canonical_key,
        Decimal(2),
        Decimal(2),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        expected.scope,
        datetime(2026, 1, 15, tzinfo=UTC),
        StateFreshness.PARTIAL,
        expected.evidence,
    )

    state = compare_expected_observed((expected,), (observed,), as_of=result.as_of)[0]

    assert state.outstanding_quantity == Decimal(2)
    assert state.freshness is StateFreshness.PARTIAL
