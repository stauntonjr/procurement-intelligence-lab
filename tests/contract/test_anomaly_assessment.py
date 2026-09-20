import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

import pytest

from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.domains.procurement.anomalies import (
    CoverageGapPolicy,
    LateCommitmentPolicy,
    MissingPurchaseOrderPolicy,
    PriceDeviationPolicy,
    QuantityMismatchPolicy,
    StaleRevisionPolicy,
    SubstitutionPolicy,
    UnresolvedIdentityPolicy,
)
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    AnomalyAssessmentInput,
    AnomalyAssessmentPolicies,
    AssessmentReason,
    AssessmentStatus,
    CoverageAttestation,
    PriceEvidence,
    QualifiedOrderLine,
    QuantityAssessmentPolicies,
    ResolutionEvidence,
    RevisionEvidence,
    ScheduleEvidence,
    SubstitutionEvidence,
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


def _all_policies() -> AnomalyAssessmentPolicies:
    return AnomalyAssessmentPolicies(
        missing_purchase_order=MissingPurchaseOrderPolicy("missing-po/v1"),
        quantity_mismatch=QuantityMismatchPolicy("quantity/v1"),
        coverage_gap=CoverageGapPolicy("coverage/v1"),
        substitution=SubstitutionPolicy("substitution/v1"),
        stale_revision=StaleRevisionPolicy("revision/v1"),
        price_deviation=PriceDeviationPolicy("price/v1", Decimal("0.50")),
        late_commitment=LateCommitmentPolicy("schedule/v1", timedelta(days=1)),
        unresolved_identity=UnresolvedIdentityPolicy("identity/v1"),
    )


def _taxonomy_service() -> AnomalyService:
    provenance = DecisionProvenance(
        local_provenance_context(),
        "full-anomaly-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="procurement-anomaly-assessment/v1",
    )
    return AnomalyService(_all_policies(), provenance, AS_OF)


@pytest.mark.contract
@pytest.mark.parametrize(
    ("case_id", "kind", "field", "value"),
    [
        (
            "substitution_positive",
            "substitution",
            "substitution",
            SubstitutionEvidence(
                "sub-1", Decimal(1), "substitute", SCOPE, AS_OF, (_evidence("substitution"),)
            ),
        ),
        (
            "revision_stale",
            "stale_revision",
            "revision",
            RevisionEvidence(
                "rev-path-1",
                "B",
                "A",
                ("A",),
                SCOPE,
                AS_OF,
                (_evidence("revision-a"), _evidence("revision-b")),
            ),
        ),
        (
            "price_deviation",
            "price_deviation",
            "planned_price",
            PriceEvidence(
                "planned-1",
                Decimal(10),
                "USD",
                "ea",
                "unit",
                SCOPE,
                AS_OF,
                (_evidence("price-planned"),),
            ),
        ),
        (
            "commitment_late",
            "late_commitment",
            "required_schedule",
            ScheduleEvidence(
                "required-1",
                date(2026, 10, 1),
                True,
                SCOPE,
                AS_OF,
                (_evidence("schedule-required"),),
            ),
        ),
        (
            "identity_unresolved",
            "unresolved_identity",
            "resolution",
            ResolutionEvidence(
                "resolution-1",
                "unresolved",
                "vendor-part-7",
                None,
                SCOPE,
                AS_OF,
                (_evidence("identity-unresolved"),),
            ),
        ),
    ],
)
def test_remaining_taxonomy_kinds_emit_qualified_results(
    context: RequestContext,
    case_id: str,
    kind: str,
    field: str,
    value: object,
) -> None:
    inputs = AnomalyAssessmentInput("GPU-A", SCOPE, AS_OF, _expected())
    if field == "planned_price":
        inputs = replace(
            inputs,
            planned_price=value,
            committed_price=PriceEvidence(
                "committed-1",
                Decimal(12),
                "USD",
                "ea",
                "unit",
                SCOPE,
                AS_OF,
                (_evidence("price-committed"),),
            ),
        )
    elif field == "required_schedule":
        inputs = replace(
            inputs,
            required_schedule=value,
            commitment=ScheduleEvidence(
                "commitment-1",
                date(2026, 10, 3),
                True,
                SCOPE,
                AS_OF,
                (_evidence("schedule-commit"),),
            ),
        )
    else:
        inputs = replace(inputs, **{field: value})

    result = next(
        item
        for item in _taxonomy_service().assess(inputs, request_context=context)
        if item.kind.value == kind
    )

    manifest_case = next(item for item in MANIFEST["cases"] if item["id"] == case_id)
    expected_status, expected_reason = manifest_case["expected"][kind]
    assert result.status.value == expected_status
    assert (result.reason.value if result.reason else None) == expected_reason
    assert result.anomaly is not None
    assert isinstance(
        value,
        (
            PriceEvidence,
            ResolutionEvidence,
            RevisionEvidence,
            ScheduleEvidence,
            SubstitutionEvidence,
        ),
    )
    assert {ref.evidence_id for ref in result.evidence} == {
        _evidence(source_id).evidence_id for source_id in manifest_case["sources"]
    }


@pytest.mark.contract
def test_independent_kinds_abstain_without_blocking_qualified_quantity(
    context: RequestContext,
) -> None:
    inputs = AnomalyAssessmentInput(
        "GPU-A",
        SCOPE,
        AS_OF,
        _expected(),
        ordered_lines=(_line("po-2", "2"),),
        planned_price=PriceEvidence(
            "planned-1",
            Decimal(10),
            "USD",
            "ea",
            "unit",
            SCOPE,
            AS_OF,
            (_evidence("price-planned"),),
        ),
        committed_price=PriceEvidence(
            "committed-1",
            Decimal(12),
            "EUR",
            "ea",
            "unit",
            SCOPE,
            AS_OF,
            (_evidence("price-committed"),),
        ),
    )
    by_kind = {
        item.kind.value: item
        for item in _taxonomy_service().assess(inputs, request_context=context)
    }

    assert by_kind["quantity_mismatch"].status is AssessmentStatus.ANOMALY
    assert by_kind["price_deviation"].status is AssessmentStatus.NOT_ASSESSED
    assert by_kind["price_deviation"].reason is AssessmentReason.INCOMPATIBLE_BASIS
    assert by_kind["late_commitment"].reason is AssessmentReason.MISSING_SCHEDULE
    assert by_kind["stale_revision"].reason is AssessmentReason.MISSING_SUPERSESSION
    assert by_kind["substitution"].reason is AssessmentReason.MISSING_RELATIONSHIP
    assert by_kind["unresolved_identity"].reason is AssessmentReason.MISSING_RESOLUTION
    assert {ref.evidence_id for ref in by_kind["quantity_mismatch"].evidence} == {
        _evidence("req-4").evidence_id,
        _evidence("po-2").evidence_id,
    }
    assert {ref.evidence_id for ref in by_kind["price_deviation"].evidence} == {
        _evidence("price-planned").evidence_id,
        _evidence("price-committed").evidence_id,
    }


@pytest.mark.contract
@pytest.mark.parametrize(
    ("price_changes", "reason"),
    [
        ({"current": False}, AssessmentReason.STALE_INPUT),
        ({"conflicted": True}, AssessmentReason.CONFLICTING_INPUT),
        ({"currency": "EUR"}, AssessmentReason.INCOMPATIBLE_BASIS),
        ({"unit": "kg"}, AssessmentReason.INCOMPATIBLE_BASIS),
    ],
)
def test_price_qualification_abstains_without_blocking_other_kinds(
    context: RequestContext,
    price_changes: dict[str, object],
    reason: AssessmentReason,
) -> None:
    planned = PriceEvidence(
        "planned-1",
        Decimal(10),
        "USD",
        "ea",
        "unit",
        SCOPE,
        AS_OF,
        (_evidence("price-planned"),),
    )
    committed = replace(
        PriceEvidence(
            "committed-1",
            Decimal(12),
            "USD",
            "ea",
            "unit",
            SCOPE,
            AS_OF,
            (_evidence("price-committed"),),
        ),
        **price_changes,
    )
    result = next(
        item
        for item in _taxonomy_service().assess(
            replace(_input("order_missing"), planned_price=planned, committed_price=committed),
            request_context=context,
        )
        if item.kind.value == "price_deviation"
    )
    assert result.status is AssessmentStatus.NOT_ASSESSED
    assert result.reason is reason


@pytest.mark.contract
def test_price_and_schedule_exact_tolerance_clear_but_just_over_flags(
    context: RequestContext,
) -> None:
    planned = PriceEvidence(
        "planned-1", Decimal(0), "USD", "ea", "unit", SCOPE, AS_OF, (_evidence("price-planned"),)
    )
    required = ScheduleEvidence(
        "required-1", date(2026, 10, 1), True, SCOPE, AS_OF, (_evidence("schedule-required"),)
    )

    def statuses(price: str, commitment_day: int) -> tuple[AssessmentStatus, AssessmentStatus]:
        inputs = replace(
            _input("order_missing"),
            planned_price=planned,
            committed_price=replace(planned, input_id="committed-1", value=Decimal(price)),
            required_schedule=required,
            commitment=replace(
                required,
                input_id="commitment-1",
                value=date(2026, 10, commitment_day),
            ),
        )
        by_kind = {
            item.kind.value: item
            for item in _taxonomy_service().assess(inputs, request_context=context)
        }
        return by_kind["price_deviation"].status, by_kind["late_commitment"].status

    assert statuses("0.50", 2) == (AssessmentStatus.CLEAR, AssessmentStatus.CLEAR)
    assert statuses("0.5001", 3) == (AssessmentStatus.ANOMALY, AssessmentStatus.ANOMALY)


@pytest.mark.contract
def test_superseded_or_future_commitment_abstains(context: RequestContext) -> None:
    required = ScheduleEvidence(
        "required-1", date(2026, 10, 1), True, SCOPE, AS_OF, (_evidence("schedule-required"),)
    )
    commitment = ScheduleEvidence(
        "commitment-1", date(2026, 10, 3), True, SCOPE, AS_OF, (_evidence("schedule-commit"),)
    )
    for changed, reason in (
        (replace(commitment, superseded=True), AssessmentReason.STALE_INPUT),
        (replace(commitment, as_of=AS_OF.replace(day=20)), AssessmentReason.FUTURE_INPUT),
    ):
        result = next(
            item
            for item in _taxonomy_service().assess(
                replace(
                    _input("order_missing"),
                    required_schedule=required,
                    commitment=changed,
                ),
                request_context=context,
            )
            if item.kind.value == "late_commitment"
        )
        assert result.status is AssessmentStatus.NOT_ASSESSED
        assert result.reason is reason
