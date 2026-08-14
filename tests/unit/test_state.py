from datetime import UTC, datetime
from decimal import Decimal

from procurement_intelligence_lab.domain.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    local_provenance_context,
)
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)
from procurement_intelligence_lab.domain.state import (
    ExpectedRequirement,
    ObservedProcurement,
    StateFreshness,
    StateScope,
    compare_expected_observed,
    expected_requirements,
    project_operational_lines,
)


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        local_provenance_context(),
        "test-resolver",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def _scope() -> StateScope:
    return StateScope("tenant", "project", "site", "bom-v1")


def test_expected_state_preserves_resolved_evidence_and_scope() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    bom = Bom(
        "fixture.xlsx",
        (
            BomLine("GPU-A", "GPU", Decimal(4), Decimal(100), evidence),
            BomLine("UNKNOWN", "GPU", Decimal(8), Decimal(100), evidence),
        ),
    )
    decisions = (
        ResolutionDecision(
            "GPU-A",
            "gpu-canonical",
            ResolutionStatus.RESOLVED,
            (),
            "exact",
            _provenance(),
        ),
        ResolutionDecision(
            "UNKNOWN",
            None,
            ResolutionStatus.UNRESOLVED,
            (),
            "missing",
            _provenance(),
        ),
    )

    lines = project_operational_lines(bom, decisions)
    expected = expected_requirements(
        lines,
        scope=_scope(),
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert len(expected) == 1
    assert expected[0].required_quantity == Decimal(4)
    assert expected[0].scope == _scope()
    assert expected[0].evidence == (evidence,)


def test_expected_and_observed_state_exposes_outstanding_and_freshness() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    expected = expected_requirements(
        (
            project_operational_lines(
                Bom(
                    "fixture.xlsx",
                    (BomLine("GPU-A", "GPU", Decimal(4), Decimal(100), evidence),),
                ),
                (
                    ResolutionDecision(
                        "GPU-A",
                        "gpu-canonical",
                        ResolutionStatus.RESOLVED,
                        (),
                        "exact",
                        _provenance(),
                    ),
                ),
            )[0],
        ),
        scope=_scope(),
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
    observed = ObservedProcurement(
        "gpu-canonical",
        Decimal(4),
        Decimal(3),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        _scope(),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateFreshness.PARTIAL,
        (evidence,),
    )

    state = compare_expected_observed(
        expected,
        (observed,),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )[0]

    assert state.outstanding_quantity == Decimal(1)
    assert state.freshness is StateFreshness.PARTIAL


def test_compare_expected_observed_selects_latest_in_scope_as_of() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    expected = (
        ExpectedRequirement(
            "gpu-canonical",
            Decimal(4),
            _scope(),
            datetime(2026, 1, 1, tzinfo=UTC),
            (evidence,),
        ),
    )
    older = ObservedProcurement(
        "gpu-canonical",
        Decimal(1),
        Decimal(1),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        _scope(),
        datetime(2026, 1, 1, tzinfo=UTC),
        StateFreshness.CURRENT,
        (evidence,),
    )
    latest = ObservedProcurement(
        "gpu-canonical",
        Decimal(4),
        Decimal(3),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        _scope(),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateFreshness.PARTIAL,
        (evidence,),
    )
    other_scope = ObservedProcurement(
        "gpu-canonical",
        Decimal(4),
        Decimal(4),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        StateScope("tenant", "other-project", "site", "bom-v1"),
        datetime(2026, 1, 2, tzinfo=UTC),
        StateFreshness.CURRENT,
        (evidence,),
    )
    future = ObservedProcurement(
        "gpu-canonical",
        Decimal(4),
        Decimal(4),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        _scope(),
        datetime(2026, 1, 3, tzinfo=UTC),
        StateFreshness.CURRENT,
        (evidence,),
    )

    state = compare_expected_observed(
        expected,
        (future, other_scope, older, latest),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )[0]

    assert state.observed == latest
    assert state.outstanding_quantity == Decimal(1)
