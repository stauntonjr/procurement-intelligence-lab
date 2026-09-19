from decimal import Decimal
from hashlib import sha256
from importlib.resources import files

import pytest

from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        "reviewer",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset({Permission.READ_STATE}),
        "showcase-test",
    )


@pytest.mark.contract
@pytest.mark.parametrize(
    ("scenario", "status", "value", "governing_count"),
    (
        (ShowcaseScenario.CONFLICT, "unresolved", None, 0),
        (ShowcaseScenario.SUPERSEDED, "governed", Decimal(6), 1),
        (ShowcaseScenario.SHARED_VALUE, "governed_shared_value", Decimal(4), 2),
        (ShowcaseScenario.MISSING_APPROVAL, "unresolved", None, 0),
    ),
)
def test_showcase_discrepancy_contracts_are_policy_backed(
    scenario: ShowcaseScenario,
    status: str,
    value: Decimal | None,
    governing_count: int,
) -> None:
    result = showcase_required_quantity(scenario, request_context=_context())

    assert result.decision.status.value == status
    assert result.decision.value == value
    assert len(result.decision.governing) == governing_count
    assert result.decision.policy_id == "procurement-governing-claims/v1"
    assert result.as_of.isoformat() == "2026-01-15T00:00:00+00:00"
    assert len(result.candidates) == 2
    assert all(item.evidence.row == 2 for item in result.candidates)
    assert all(item.evidence.cells == ("A", "B", "C", "D", "E") for item in result.candidates)


@pytest.mark.contract
def test_showcase_fixture_hashes_and_original_quantities_are_frozen() -> None:
    expected = {
        "showcase_bom_revision_a.xlsx": "818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8",
        "showcase_bom_revision_b.xlsx": "c12a72195c783343e24a05eb77ba9cb0145b889f5b39a66cc449d247c29bfdf2",
        "showcase_bom_revision_b_equal.xlsx": "818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8",
    }

    for name, content_hash in expected.items():
        raw = files("procurement_intelligence_lab.examples").joinpath(name).read_bytes()
        assert sha256(raw).hexdigest() == content_hash
