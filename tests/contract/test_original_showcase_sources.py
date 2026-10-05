"""Original fixtures preserve domain identity through a source-selected review bridge."""

import json
import shutil
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.showcase_sources import ShowcaseSources
from procurement_intelligence_lab.application.corpus_investigation import InvestigationRequest
from procurement_intelligence_lab.application.original_showcase import OriginalShowcaseInvestigator
from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_order_comparison,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError, CorpusNotFoundError

CONTEXT = RequestContext(
    "local-demo",
    "synthetic-tenant",
    "synthetic-project",
    "synthetic-site",
    frozenset(Permission),
    "test",
)
AS_OF = datetime(2026, 1, 15, tzinfo=UTC)
CASES = [
    ("showcase-a-order", ShowcaseScenario.ORDER_MISMATCH, "4", "2", "anomaly", None),
    (
        "showcase-a-b-order",
        ShowcaseScenario.ORDER_UNRESOLVED,
        None,
        "2",
        "not_assessed",
        "unresolved_requirement",
    ),
    (
        "showcase-a-only",
        ShowcaseScenario.ORDER_MISSING,
        "4",
        None,
        "not_assessed",
        "missing_observation",
    ),
]


@pytest.mark.parametrize("selection,scenario,required,observed,status,reason", CASES)
def test_original_bridge_preserves_complete_policy_identity(
    selection: str,
    scenario: ShowcaseScenario,
    required: str | None,
    observed: str | None,
    status: str,
    reason: str | None,
) -> None:
    sources = ShowcaseSources(selection)
    actual = OriginalShowcaseInvestigator(sources, scenario).investigate(
        InvestigationRequest("GPU-A", AS_OF), context=CONTEXT
    )
    direct = showcase_order_comparison(scenario, request_context=CONTEXT)
    quantity = next(a for a in direct.assessments if a.kind.value == "quantity_mismatch")
    assert actual.governed == direct.requirement.governed_state
    actual_assessment, direct_assessment = asdict(actual.assessment), asdict(quantity)
    for assessment in (actual_assessment, direct_assessment):
        if assessment["anomaly"]:
            assessment["anomaly"]["provenance"]["context"].pop("started_at")
    assert actual_assessment == direct_assessment
    assert actual.ordered_quantity == direct.ordered_quantity
    assert (
        str(actual.governed.expected.required_quantity) if actual.governed.expected else None
    ) == required
    assert (
        str(actual.ordered_quantity) if actual.ordered_quantity is not None else None
    ) == observed
    assert actual.assessment.status.value == status
    assert (actual.assessment.reason.value if actual.assessment.reason else None) == reason
    expected = {c.evidence.evidence_id for c in direct.requirement.candidates} | {
        r.evidence_id for r in direct.order_evidence
    }
    assert {r.evidence_id for r in actual.evidence} == expected
    assert sources.items(context=CONTEXT) == ("GPU-A",)
    assert actual.snapshot_id == sources.snapshot_id(context=CONTEXT)
    for ref in actual.evidence:
        source = sources.source_by_id(ref.evidence_id, context=CONTEXT)
        assert source.evidence == ref and source.cells[0] == "GPU-A"
        assert source.highlighted_columns
    assert sources.snapshot_id(context=CONTEXT) == actual.snapshot_id


@pytest.mark.parametrize(
    "field,value", [("tenant_id", "foreign"), ("project_id", "atlas"), ("site_id", "lab")]
)
def test_source_scope_precedes_file_access(tmp_path: Path, field: str, value: str) -> None:
    sources = ShowcaseSources("showcase-a-order", root=tmp_path)
    with pytest.raises(ScopeAuthorizationError):
        sources.items(context=replace(CONTEXT, **{field: value}))


def test_source_permissions_and_membership() -> None:
    sources = ShowcaseSources("showcase-a-only")
    with pytest.raises(ScopeAuthorizationError):
        sources.items(context=replace(CONTEXT, permissions=frozenset()))
    other = ShowcaseSources("showcase-a-order")
    order = next(
        r
        for r in OriginalShowcaseInvestigator(other, ShowcaseScenario.ORDER_MISMATCH)
        .investigate(InvestigationRequest("GPU-A", AS_OF), context=CONTEXT)
        .evidence
        if "order_short" in r.artifact_id
    )
    with pytest.raises(CorpusNotFoundError):
        sources.source_by_id(order.evidence_id, context=CONTEXT)


@pytest.mark.parametrize(
    "item,cutoff",
    [
        ("GPU-B", AS_OF),
        ("", AS_OF),
        ("GPU-A", datetime(2026, 1, 14, tzinfo=UTC)),
        ("GPU-A", datetime(2026, 1, 16, tzinfo=UTC)),
    ],
)
def test_original_fixed_request_does_not_substitute_item_or_cutoff(
    item: str, cutoff: datetime
) -> None:
    with pytest.raises(ValueError):
        OriginalShowcaseInvestigator(
            ShowcaseSources("showcase-a-order"), ShowcaseScenario.ORDER_MISMATCH
        ).investigate(InvestigationRequest(item, cutoff), context=CONTEXT)


def copy_sources(tmp_path: Path) -> Path:
    root = ShowcaseSources("showcase-a-order").root
    for name in (
        "showcase_review_sources_v1.json",
        "showcase_bom_revision_a.xlsx",
        "showcase_bom_revision_b.xlsx",
        "showcase_order_short.xlsx",
    ):
        shutil.copy2(root / name, tmp_path / name)
    return tmp_path


@pytest.mark.parametrize(
    "damage", ["hash", "missing", "manifest", "version", "unknown_path", "duplicate", "symlink"]
)
def test_original_admission_rejects_invalid_sources(tmp_path: Path, damage: str) -> None:
    root = copy_sources(tmp_path)
    manifest = root / "showcase_review_sources_v1.json"
    if damage == "hash":
        (root / "showcase_bom_revision_a.xlsx").write_bytes(b"tampered")
    elif damage == "missing":
        (root / "showcase_order_short.xlsx").unlink()
    elif damage == "symlink":
        p = root / "showcase_order_short.xlsx"
        p.unlink()
        p.symlink_to(root / "showcase_bom_revision_a.xlsx")
    elif damage == "manifest":
        manifest.write_text("{")
    else:
        raw = json.loads(manifest.read_text())
        if damage == "version":
            raw["schema_version"] = 2
        elif damage == "unknown_path":
            raw["documents"][0]["path"] = "../outside.xlsx"
        else:
            raw["documents"].append(raw["documents"][0])
        manifest.write_text(json.dumps(raw))
    with pytest.raises(CorpusAdmissionError):
        ShowcaseSources("showcase-a-order", root=root).items(context=CONTEXT)


def test_unknown_source_and_scenario_are_rejected() -> None:
    with pytest.raises(ValueError):
        ShowcaseSources("invented")
    with pytest.raises(ValueError):
        OriginalShowcaseInvestigator(
            ShowcaseSources("showcase-a-order"), ShowcaseScenario.ORDER_MATCHED
        )


def test_changed_source_selection_has_a_distinct_snapshot() -> None:
    assert len({ShowcaseSources(c[0]).snapshot_id(context=CONTEXT) for c in CASES}) == 3


@pytest.mark.parametrize("selection", ["showcase-a-b-order", "showcase-a-only"])
def test_service_refuses_a_mismatched_source_inventory(selection: str) -> None:
    with pytest.raises(CorpusAdmissionError):
        OriginalShowcaseInvestigator(
            ShowcaseSources(selection), ShowcaseScenario.ORDER_MISMATCH
        ).investigate(InvestigationRequest("GPU-A", AS_OF), context=CONTEXT)
