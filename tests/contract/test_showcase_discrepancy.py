import json
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files

import pytest

from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_anomaly_assessment,
    showcase_order_comparison,
    showcase_required_quantity,
)
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    AssessmentReason,
    AssessmentStatus,
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
        "showcase_order_short.xlsx": "2e1fc82884b49252e1fd61d4ac6ce8e5466c883132d5e1dd3871dcb6fcb31337",
        "showcase_order_matched.xlsx": "9c1a302e151252c91137d94bc1f41169e4333de36c32d86883eeef049acd9903",
        "showcase_bom_revision_a.xlsx": "818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8",
        "showcase_bom_revision_b.xlsx": "c12a72195c783343e24a05eb77ba9cb0145b889f5b39a66cc449d247c29bfdf2",
        "showcase_bom_revision_b_equal.xlsx": "818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8",
    }

    for name, content_hash in expected.items():
        raw = files("procurement_intelligence_lab.examples").joinpath(name).read_bytes()
        assert sha256(raw).hexdigest() == content_hash


@pytest.mark.contract
def test_order_comparison_is_repeatable_and_keeps_governance_separate() -> None:
    first = showcase_order_comparison(ShowcaseScenario.ORDER_MISMATCH, request_context=_context())
    again = showcase_order_comparison(ShowcaseScenario.ORDER_MISMATCH, request_context=_context())
    assert first.anomalies[0].anomaly_id == again.anomalies[0].anomaly_id
    expected = first.requirement.governed_state.expected
    assert expected is not None
    assert first.anomalies[0].scope == expected.scope
    assert all(ref.artifact_id.startswith("showcase:") for ref in first.anomalies[0].evidence)
    assert first.anomalies[0].provenance.context.input_snapshot_ids == tuple(
        ref.evidence_id for ref in first.anomalies[0].evidence
    )
    assert first.requirement.decision.value == Decimal(4)
    with pytest.raises(ValueError, match="unsupported order comparison"):
        showcase_order_comparison(ShowcaseScenario.CONFLICT, request_context=_context())


@pytest.mark.contract
def test_order_showcase_uses_qualified_assessment_service() -> None:
    mismatch = showcase_order_comparison(
        ShowcaseScenario.ORDER_MISMATCH, request_context=_context()
    )
    missing = showcase_order_comparison(ShowcaseScenario.ORDER_MISSING, request_context=_context())

    mismatch_by_kind = {item.kind.value: item for item in mismatch.assessments}
    missing_by_kind = {item.kind.value: item for item in missing.assessments}
    assert mismatch_by_kind["quantity_mismatch"].status is AssessmentStatus.ANOMALY
    assert mismatch_by_kind["missing_po"].status is AssessmentStatus.NOT_ASSESSED
    assert mismatch_by_kind["missing_po"].reason is AssessmentReason.MISSING_COVERAGE
    assert missing_by_kind["missing_po"].status is AssessmentStatus.NOT_ASSESSED
    assert missing_by_kind["missing_po"].reason is AssessmentReason.MISSING_OBSERVATION
    assert missing_by_kind["quantity_mismatch"].status is AssessmentStatus.NOT_ASSESSED


@pytest.mark.contract
def test_public_anomaly_inputs_are_derived_from_packaged_records() -> None:
    sources = json.loads(
        files("procurement_intelligence_lab.examples")
        .joinpath("anomaly_sources_v1.json")
        .read_text()
    )
    lifecycle = showcase_anomaly_assessment(
        ShowcaseScenario.LIFECYCLE_REVIEWED, request_context=_context()
    )
    substitution = showcase_anomaly_assessment(
        ShowcaseScenario.SUBSTITUTION, request_context=_context()
    )
    revision = showcase_anomaly_assessment(
        ShowcaseScenario.STALE_REVISION, request_context=_context()
    )

    line = lifecycle.inputs.ordered_lines[0]
    assert line.quantity == Decimal(sources["po-2"]["ordered_quantity"])
    assert line.unit == sources["po-2"]["unit"]
    assert line.approved is sources["po-2"]["approved"]
    assert substitution.inputs.substitution is not None
    assert substitution.inputs.substitution.approved is sources["substitution"]["approved"]
    assert substitution.inputs.substitution.ambiguous is sources["substitution"]["ambiguous"]
    assert revision.inputs.revision is not None
    assert revision.inputs.revision.authoritative is sources["revision-b"]["authoritative"]
    assert revision.inputs.revision.ambiguous is sources["revision-b"]["ambiguous"]
    assert (
        list(revision.inputs.revision.supersession_edge_ids)
        == sources["revision-b"]["supersession_edge_ids"]
    )
