import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

import pytest

from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.domains.procurement.anomalies import (
    CoverageGapPolicy,
    MissingPurchaseOrderPolicy,
    QuantityMismatchPolicy,
)
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    AnomalyAssessmentInput,
    AssessmentReason,
    AssessmentStatus,
    CoverageAttestation,
    QualifiedOrderLine,
    QuantityAssessmentPolicies,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import ExpectedRequirement
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)

MANIFEST = json.loads((Path(__file__).parents[2] / "evals/anomalies/v1/manifest.json").read_text())
AS_OF = datetime.fromisoformat(MANIFEST["as_of"])
SCOPE = StateScope("tenant-demo", "project-demo", "site-demo", "governed-v1")


@pytest.mark.contract
def test_packaged_anomaly_sources_match_the_admitted_manifest() -> None:
    packaged = json.loads(
        files("procurement_intelligence_lab.examples")
        .joinpath("anomaly_sources_v1.json")
        .read_text()
    )
    assert packaged == {
        source_id: source["payload"] for source_id, source in MANIFEST["sources"].items()
    }


def _evidence(source_id: str) -> EvidenceRef:
    source = MANIFEST["sources"][source_id]
    return EvidenceRef(
        f"anomaly-corpus:{source_id}",
        source["sha256"],
        RecordLocation("anomaly-corpus/v1", source_id),
    )


def _expected() -> ExpectedRequirement:
    return ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, (_evidence("req-4"),))


def _line(
    source_id: str,
    quantity: str,
    *,
    assertion_id: str | None = None,
    scope: StateScope = SCOPE,
    as_of: datetime = AS_OF,
) -> QualifiedOrderLine:
    return QualifiedOrderLine(
        line_id=source_id,
        assertion_id=assertion_id or source_id,
        quantity=Decimal(quantity),
        unit="ea",
        scope=scope,
        as_of=as_of,
        approved=True,
        evidence=(_evidence(source_id),),
    )


def _coverage(source_id: str, *, complete: bool) -> CoverageAttestation:
    return CoverageAttestation(
        attestation_id=source_id,
        subject_key="GPU-A",
        scope=SCOPE,
        as_of=AS_OF,
        complete=complete,
        current=True,
        authoritative=True,
        evidence=(_evidence(source_id),),
    )


def _input(case: str) -> AnomalyAssessmentInput:
    if case == "order_missing":
        return AnomalyAssessmentInput("GPU-A", SCOPE, AS_OF, _expected())
    if case == "order_unresolved":
        return AnomalyAssessmentInput(
            "GPU-A",
            SCOPE,
            AS_OF,
            None,
            governance_decision_ids=("decision-unresolved",),
            governance_evidence=(_evidence("req-4"),),
            ordered_lines=(_line("po-2", "2"),),
            coverage=_coverage("coverage-complete", complete=True),
        )
    if case == "complete_empty_orders":
        return AnomalyAssessmentInput(
            "GPU-A",
            SCOPE,
            AS_OF,
            _expected(),
            governance_decision_ids=("decision-required-4",),
            coverage=_coverage("coverage-complete", complete=True),
        )
    if case == "incomplete_empty_orders":
        return AnomalyAssessmentInput(
            "GPU-A",
            SCOPE,
            AS_OF,
            _expected(),
            governance_decision_ids=("decision-required-4",),
            coverage=_coverage("coverage-incomplete", complete=False),
        )
    raise AssertionError(case)


@pytest.fixture
def context() -> RequestContext:
    return RequestContext(
        "reviewer",
        "tenant-demo",
        "project-demo",
        "site-demo",
        frozenset({Permission.READ_STATE}),
        "assessment-contract",
    )


@pytest.fixture
def service() -> AnomalyService:
    policies = QuantityAssessmentPolicies(
        MissingPurchaseOrderPolicy("missing-po/v1"),
        QuantityMismatchPolicy("quantity/v1"),
        CoverageGapPolicy("coverage/v1"),
    )
    provenance = DecisionProvenance(
        replace(
            local_provenance_context(),
            workflow_name="anomaly-assessment-contract",
            input_snapshot_ids=(),
        ),
        "qualified-quantity-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="synthetic-anomaly-policy/v1",
    )
    return AnomalyService(policies, provenance, AS_OF)


@pytest.mark.contract
@pytest.mark.parametrize(
    "case, status, reason",
    [
        ("order_missing", "not_assessed", "missing_observation"),
        ("order_unresolved", "not_assessed", "unresolved_requirement"),
        ("complete_empty_orders", "anomaly", None),
        ("incomplete_empty_orders", "not_assessed", "incomplete_coverage"),
    ],
)
def test_missing_po_requires_positive_coverage_evidence(
    service: AnomalyService,
    context: RequestContext,
    case: str,
    status: str,
    reason: str | None,
) -> None:
    results = service.assess(_input(case), request_context=context)
    result = next(item for item in results if item.kind.value == "missing_po")
    assert result.status.value == status
    assert (result.reason.value if result.reason else None) == reason


@pytest.mark.contract
def test_quantity_aggregates_distinct_lines_and_deduplicates_exact_replay(
    service: AnomalyService, context: RequestContext
) -> None:
    one = _line("po-line-a", "1")
    three = _line("po-line-b", "3")
    assessment_input = AnomalyAssessmentInput(
        "GPU-A",
        SCOPE,
        AS_OF,
        _expected(),
        governance_decision_ids=("decision-required-4",),
        ordered_lines=(three, one, one),
        coverage=_coverage("coverage-complete", complete=True),
    )

    first = service.assess(assessment_input, request_context=context)
    reordered = service.assess(
        replace(assessment_input, ordered_lines=tuple(reversed(assessment_input.ordered_lines))),
        request_context=context,
    )
    quantity = next(item for item in first if item.kind.value == "quantity_mismatch")
    quantity_reordered = next(item for item in reordered if item.kind.value == "quantity_mismatch")

    assert quantity.status is AssessmentStatus.CLEAR
    assert quantity.input_ids == ("po-line-a", "po-line-b")
    assert quantity.assessment_id == quantity_reordered.assessment_id


@pytest.mark.contract
def test_conflicting_reuse_of_assertion_id_abstains(
    service: AnomalyService, context: RequestContext
) -> None:
    first = _line("po-2", "2", assertion_id="same-assertion")
    conflict = _line("po-conflict", "3", assertion_id="same-assertion")
    assessment_input = AnomalyAssessmentInput(
        "GPU-A",
        SCOPE,
        AS_OF,
        _expected(),
        ordered_lines=(first, conflict),
        coverage=_coverage("coverage-complete", complete=True),
    )

    result = next(
        item
        for item in service.assess(assessment_input, request_context=context)
        if item.kind.value == "quantity_mismatch"
    )

    assert result.status is AssessmentStatus.NOT_ASSESSED
    assert result.reason is AssessmentReason.CONFLICTING_INPUT
    assert {ref.evidence_id for ref in result.evidence} == {
        _evidence("req-4").evidence_id,
        _evidence("po-2").evidence_id,
        _evidence("po-conflict").evidence_id,
        _evidence("coverage-complete").evidence_id,
    }


@pytest.mark.contract
def test_scope_and_time_rejections_are_explicit(
    service: AnomalyService, context: RequestContext
) -> None:
    other_scope = replace(SCOPE, site_id="site-other")
    future = AS_OF.replace(day=20)
    for line, reason in (
        (_line("po-2", "2", scope=other_scope), AssessmentReason.SCOPE_MISMATCH),
        (_line("po-2", "2", as_of=future), AssessmentReason.FUTURE_INPUT),
    ):
        result = next(
            item
            for item in service.assess(
                AnomalyAssessmentInput(
                    "GPU-A",
                    SCOPE,
                    AS_OF,
                    _expected(),
                    ordered_lines=(line,),
                    coverage=_coverage("coverage-complete", complete=True),
                ),
                request_context=context,
            )
            if item.kind.value == "quantity_mismatch"
        )
        assert result.status is AssessmentStatus.NOT_ASSESSED
        assert result.reason is reason
        disposition = dict(result.input_dispositions)
        assert disposition[line.line_id] == (
            "rejected_scope" if reason is AssessmentReason.SCOPE_MISMATCH else "rejected_future"
        )


@pytest.mark.contract
def test_exact_tolerance_is_clear_and_fractional_overage_is_anomaly(
    service: AnomalyService, context: RequestContext
) -> None:
    tolerant = replace(
        service,
        policies=replace(
            service.policies,
            quantity_mismatch=QuantityMismatchPolicy("quantity/v1", Decimal("0.5")),
        ),
    )
    at_boundary = replace(_line("po-4", "4"), quantity=Decimal("4.5"))
    over_boundary = replace(_line("po-4", "4"), quantity=Decimal("4.5001"))

    def quantity_status(line: QualifiedOrderLine) -> AssessmentStatus:
        results = tolerant.assess(
            AnomalyAssessmentInput("GPU-A", SCOPE, AS_OF, _expected(), ordered_lines=(line,)),
            request_context=context,
        )
        return next(item.status for item in results if item.kind.value == "quantity_mismatch")

    assert quantity_status(at_boundary) is AssessmentStatus.CLEAR
    assert quantity_status(over_boundary) is AssessmentStatus.ANOMALY


@pytest.mark.contract
def test_approved_zero_line_is_not_misclassified_as_missing_po(
    service: AnomalyService, context: RequestContext
) -> None:
    results = service.assess(
        AnomalyAssessmentInput(
            "GPU-A",
            SCOPE,
            AS_OF,
            _expected(),
            ordered_lines=(_line("po-zero", "0"),),
            coverage=_coverage("coverage-complete", complete=True),
        ),
        request_context=context,
    )
    by_kind = {item.kind.value: item for item in results}
    assert by_kind["missing_po"].status is AssessmentStatus.CLEAR
    assert by_kind["quantity_mismatch"].status is AssessmentStatus.ANOMALY


@pytest.mark.contract
def test_input_objects_reject_naive_time_and_missing_evidence() -> None:
    with pytest.raises(TemporalContractError, match="timezone-aware"):
        replace(_line("po-2", "2"), as_of=datetime(2026, 9, 19))  # noqa: DTZ001
    with pytest.raises(SemanticContractError, match="requires evidence"):
        replace(_line("po-2", "2"), evidence=())


@pytest.mark.contract
@pytest.mark.parametrize("quantity", [Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_order_lines_reject_invalid_quantities(quantity: Decimal) -> None:
    with pytest.raises(SemanticContractError, match="finite and non-negative"):
        replace(_line("po-2", "2"), quantity=quantity)
