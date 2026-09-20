"""Versioned synthetic discrepancy scenarios for the read-only inspector."""

import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from importlib.resources import as_file, files
from typing import cast

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
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
    AnomalyAssessment,
    AnomalyAssessmentInput,
    AnomalyAssessmentPolicies,
    CoverageAttestation,
    PriceEvidence,
    QualifiedOrderLine,
    QuantityAssessmentPolicies,
    ResolutionEvidence,
    RevisionEvidence,
    ScheduleEvidence,
    SubstitutionEvidence,
)
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimDecision,
    GoverningPredicate,
    GoverningSourceType,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import (
    ExpectedRequirement,
    GovernedRequiredQuantityState,
    ProcurementStateBasis,
    project_governed_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly, AnomalyStatus
from procurement_intelligence_lab.platform.semantics.anomaly_lifecycle import (
    AnomalyLifecycleEvent,
    LifecycleEvidenceKind,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext, StateScope


class ShowcaseScenario(StrEnum):
    ORDER_MISMATCH = "order_mismatch"
    ORDER_MATCHED = "order_matched"
    ORDER_MISSING = "order_missing"
    ORDER_UNRESOLVED = "order_unresolved"
    CONFLICT = "conflict"
    SUPERSEDED = "superseded"
    SHARED_VALUE = "shared_value"
    MISSING_APPROVAL = "missing_approval"
    QUALIFIED_MISSING_PO = "qualified_missing_po"
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    PRICE_DEVIATION = "price_deviation"
    LATE_COMMITMENT = "late_commitment"
    STALE_REVISION = "stale_revision"
    SUBSTITUTION = "substitution"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    LIFECYCLE_SUPPRESSED = "lifecycle_suppressed"
    LIFECYCLE_REVIEWED = "lifecycle_reviewed"
    LIFECYCLE_RESOLVED = "lifecycle_resolved"


_AS_OF = datetime(2026, 1, 15, tzinfo=UTC)
_SCOPE = ("synthetic-tenant", "synthetic-project", "synthetic-site")
_ANOMALY_AS_OF = datetime(2026, 9, 19, 12, tzinfo=UTC)
_ANOMALY_SCOPE = StateScope(*_SCOPE, "governed-v1")


@dataclass(frozen=True)
class ShowcaseRequiredQuantityResult:
    scenario: ShowcaseScenario
    as_of: datetime
    candidates: tuple[GoverningClaim, ...]
    decision: GoverningClaimDecision
    governed_state: GovernedRequiredQuantityState


def showcase_required_quantity(
    scenario: ShowcaseScenario,
    *,
    request_context: RequestContext,
) -> ShowcaseRequiredQuantityResult:
    """Evaluate one fixed scenario through the v1 governing-claim policy."""

    candidates = _scenario_candidates(scenario)
    governed_state = project_governed_required_quantity(
        candidates,
        canonical_key="GPU-A",
        request_context=request_context,
        as_of=_AS_OF,
    )
    return ShowcaseRequiredQuantityResult(
        scenario,
        _AS_OF,
        candidates,
        governed_state.decision,
        governed_state,
    )


def _scenario_candidates(scenario: ShowcaseScenario) -> tuple[GoverningClaim, ...]:
    if scenario in (
        ShowcaseScenario.ORDER_MISMATCH,
        ShowcaseScenario.ORDER_MATCHED,
        ShowcaseScenario.ORDER_MISSING,
    ):
        return (_claim("A"),)
    if scenario in (ShowcaseScenario.CONFLICT, ShowcaseScenario.ORDER_UNRESOLVED):
        return (_claim("A"), _claim("B"))
    if scenario is ShowcaseScenario.SUPERSEDED:
        return (
            _claim("A"),
            _claim("B", effective_from=datetime(2026, 1, 10, tzinfo=UTC), supersedes=("A",)),
        )
    if scenario is ShowcaseScenario.SHARED_VALUE:
        return (_claim("A"), _claim("B-equal"))
    if scenario is ShowcaseScenario.MISSING_APPROVAL:
        return (
            _claim("A", effective_until=datetime(2026, 1, 10, tzinfo=UTC)),
            _claim(
                "B",
                effective_from=datetime(2026, 1, 10, tzinfo=UTC),
                approved_at=None,
            ),
        )
    raise ValueError(f"unsupported showcase scenario: {scenario!r}")


def _claim(
    revision: str,
    *,
    approved_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC),
    effective_from: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    effective_until: datetime | None = None,
    supersedes: tuple[str, ...] = (),
) -> GoverningClaim:
    resource_name = {
        "A": "showcase_bom_revision_a.xlsx",
        "B": "showcase_bom_revision_b.xlsx",
        "B-equal": "showcase_bom_revision_b_equal.xlsx",
    }[revision]
    resource = files("procurement_intelligence_lab.examples").joinpath(resource_name)
    with as_file(resource) as path:
        evidence = read_bom(path, artifact_id=f"showcase:{resource_name}").lines[0].evidence
        source_row = read_source_row(path, evidence=evidence)
    try:
        unit = source_row.cells[source_row.headers.index("Unit")]
        quantity = source_row.cells[source_row.headers.index("Quantity")]
    except ValueError as error:
        raise ValueError("showcase source row lacks a required quantity or unit column") from error
    return GoverningClaim(
        claim_id=f"showcase:{revision}",
        canonical_key="GPU-A",
        predicate=GoverningPredicate.REQUIRED_QUANTITY,
        value=Decimal(quantity),
        unit=unit,
        source_type=GoverningSourceType.APPROVED_BOM_REVISION,
        scope=StateScope(*_SCOPE, revision),
        evidence=evidence,
        revision_id=revision,
        supersedes_revision_ids=supersedes,
        approved_at=approved_at,
        effective_from=effective_from,
        effective_until=effective_until,
        document_at=datetime(2025, 12, 31, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


ORDER_SCENARIOS = frozenset(
    {
        ShowcaseScenario.ORDER_MISMATCH,
        ShowcaseScenario.ORDER_MATCHED,
        ShowcaseScenario.ORDER_MISSING,
        ShowcaseScenario.ORDER_UNRESOLVED,
    }
)
ORDER_POLICY = QuantityMismatchPolicy("procurement-showcase-order-quantity/v1")


@dataclass(frozen=True)
class ShowcaseOrderComparison:
    requirement: ShowcaseRequiredQuantityResult
    ordered_quantity: Decimal | None
    order_evidence: tuple[EvidenceRef, ...]
    status: str
    reason: str | None
    anomalies: tuple[Anomaly, ...]
    assessments: tuple[AnomalyAssessment, ...]


def showcase_order_comparison(
    scenario: ShowcaseScenario, *, request_context: RequestContext
) -> ShowcaseOrderComparison:
    """Compare one explicitly admitted order row, without inventing receipt or PO state."""
    if scenario not in ORDER_SCENARIOS:
        raise SemanticContractError("unsupported order comparison scenario")
    requirement = showcase_required_quantity(scenario, request_context=request_context)
    ordered = None
    evidence: tuple[EvidenceRef, ...] = ()
    if scenario is not ShowcaseScenario.ORDER_MISSING:
        name = (
            "showcase_order_matched.xlsx"
            if scenario is ShowcaseScenario.ORDER_MATCHED
            else "showcase_order_short.xlsx"
        )
        resource = files("procurement_intelligence_lab.examples").joinpath(name)
        with as_file(resource) as path:
            rows = read_bom(path, artifact_id=f"showcase:{name}").lines
            if len(rows) != 1 or rows[0].sku != "GPU-A":
                raise SemanticContractError("synthetic order requires one GPU-A row")
            row = rows[0]
            source = read_source_row(path, evidence=row.evidence)
            if source.cells[source.headers.index("Unit")] != "each":
                raise SemanticContractError("synthetic order unit must be each")
            ordered, evidence = row.quantity, (row.evidence,)
    expected = requirement.governed_state.expected
    if expected is None or ordered is None:
        return ShowcaseOrderComparison(
            requirement,
            ordered,
            evidence,
            "not_assessed",
            "unresolved_requirement" if expected is None else "missing_observation",
            (),
            _showcase_assessments(
                requirement,
                None,
                (),
                request_context=request_context,
            ),
        )
    assessments = _showcase_assessments(
        requirement,
        ordered,
        evidence,
        request_context=request_context,
    )
    quantity = next(item for item in assessments if item.kind.value == "quantity_mismatch")
    anomaly = quantity.anomaly
    return ShowcaseOrderComparison(
        requirement,
        ordered,
        evidence,
        "quantity_mismatch" if anomaly else "matched",
        None,
        (anomaly,) if anomaly else (),
        assessments,
    )


def _showcase_assessments(
    requirement: ShowcaseRequiredQuantityResult,
    ordered: Decimal | None,
    evidence: tuple[EvidenceRef, ...],
    *,
    request_context: RequestContext,
) -> tuple[AnomalyAssessment, ...]:
    expected = requirement.governed_state.expected
    scope = expected.scope if expected is not None else StateScope(*_SCOPE, "unresolved")
    ordered_lines = (
        (
            QualifiedOrderLine(
                line_id=evidence[0].evidence_id,
                assertion_id=evidence[0].evidence_id,
                quantity=ordered,
                unit="each",
                scope=scope,
                as_of=requirement.as_of,
                approved=True,
                evidence=evidence,
            ),
        )
        if ordered is not None
        else ()
    )
    policies = QuantityAssessmentPolicies(
        MissingPurchaseOrderPolicy("procurement-showcase-order-missing/v1"),
        ORDER_POLICY,
        CoverageGapPolicy("procurement-showcase-order-coverage/v1"),
    )
    all_evidence = tuple(
        {
            ref.evidence_id: ref
            for ref in (tuple(item.evidence for item in requirement.candidates) + evidence)
        }.values()
    )
    context = replace(
        local_provenance_context(),
        workflow_name="showcase-order-comparison",
        config_digest=policies.digest,
        input_snapshot_ids=tuple(sorted(ref.evidence_id for ref in all_evidence)),
    )
    provenance = DecisionProvenance(
        context,
        "qualified-quantity-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="procurement-anomaly-assessment/v1",
    )
    service = AnomalyService(policies, provenance, requirement.as_of)
    return service.assess(
        AnomalyAssessmentInput(
            "GPU-A",
            scope,
            requirement.as_of,
            expected,
            expected_unit="each",
            governance_decision_ids=(requirement.decision.decision_id,),
            governance_evidence=tuple(item.evidence for item in requirement.candidates),
            ordered_lines=ordered_lines,
        ),
        request_context=request_context,
    )


TAXONOMY_SCENARIOS = frozenset(
    {
        ShowcaseScenario.QUALIFIED_MISSING_PO,
        ShowcaseScenario.INCOMPLETE_COVERAGE,
        ShowcaseScenario.PRICE_DEVIATION,
        ShowcaseScenario.LATE_COMMITMENT,
        ShowcaseScenario.STALE_REVISION,
        ShowcaseScenario.SUBSTITUTION,
        ShowcaseScenario.UNRESOLVED_IDENTITY,
        ShowcaseScenario.LIFECYCLE_SUPPRESSED,
        ShowcaseScenario.LIFECYCLE_REVIEWED,
        ShowcaseScenario.LIFECYCLE_RESOLVED,
    }
)


@dataclass(frozen=True)
class ShowcaseAnomalyResult:
    scenario: ShowcaseScenario
    inputs: AnomalyAssessmentInput
    assessments: tuple[AnomalyAssessment, ...]
    selected: AnomalyAssessment
    lifecycle_history: tuple[AnomalyLifecycleEvent, ...]
    projected_anomaly: Anomaly


def _anomaly_sources() -> dict[str, dict[str, object]]:
    resource = files("procurement_intelligence_lab.examples").joinpath("anomaly_sources_v1.json")
    return json.loads(resource.read_text())


def _source_record(source_id: str) -> dict[str, object]:
    return _anomaly_sources()[source_id]


def anomaly_source_evidence(source_id: str) -> EvidenceRef:
    """Build the stable evidence identity for one packaged anomaly-corpus record."""
    payload = _source_record(source_id)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return EvidenceRef(
        f"anomaly-corpus:{source_id}",
        sha256(canonical.encode()).hexdigest(),
        RecordLocation("anomaly-corpus/v1", source_id),
    )


def lifecycle_event_evidence(event: AnomalyLifecycleEvent) -> tuple[EvidenceRef, ...]:
    """Expose event evidence as immutable fixture records, not mutation controls."""
    return tuple(
        EvidenceRef(
            "anomaly-lifecycle:v1",
            sha256(_lifecycle_event_canonical(event, evidence_id).encode()).hexdigest(),
            RecordLocation("anomaly-lifecycle/v1", evidence_id),
        )
        for evidence_id in event.evidence_ids
    )


def _lifecycle_event_canonical(event: AnomalyLifecycleEvent, evidence_id: str) -> str:
    return json.dumps(
        lifecycle_event_source_record(event, evidence_id),
        sort_keys=True,
        separators=(",", ":"),
    )


def lifecycle_event_source_record(
    event: AnomalyLifecycleEvent, evidence_id: str
) -> dict[str, object]:
    return {
        "actor_ref": event.actor_ref,
        "anomaly_id": event.anomaly_id,
        "evidence_id": evidence_id,
        "evidence_kind": event.evidence_kind.value,
        "event_id": event.event_id,
        "new_status": event.new_status.value,
        "occurred_at": event.occurred_at.isoformat(),
        "policy_id": event.policy_id,
        "previous_status": event.previous_status.value,
        "expected_prior_event_id": event.expected_prior_event_id,
        "reason": event.reason,
        "recorded_at": event.recorded_at.isoformat(),
        "scope": {
            "tenant_id": event.scope.tenant_id,
            "project_id": event.scope.project_id,
            "site_id": event.scope.site_id,
            "version": event.scope.version,
        },
    }


def showcase_anomaly_assessment(
    scenario: ShowcaseScenario, *, request_context: RequestContext
) -> ShowcaseAnomalyResult:
    """Assess one fixed corpus scenario and optionally replay its read-only lifecycle."""
    if scenario not in TAXONOMY_SCENARIOS:
        raise SemanticContractError("unsupported anomaly showcase scenario")
    requirement = _source_record("req-4")
    expected = ExpectedRequirement(
        "GPU-A",
        Decimal(str(requirement["required_quantity"])),
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        (anomaly_source_evidence("req-4"),),
        ProcurementStateBasis.RECONCILED,
    )
    inputs = AnomalyAssessmentInput(
        "GPU-A",
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        expected,
        governance_decision_ids=("showcase-required-4",),
        governance_evidence=expected.evidence,
    )
    selected_kind = {
        ShowcaseScenario.QUALIFIED_MISSING_PO: "missing_po",
        ShowcaseScenario.INCOMPLETE_COVERAGE: "coverage_gap",
        ShowcaseScenario.PRICE_DEVIATION: "price_deviation",
        ShowcaseScenario.LATE_COMMITMENT: "late_commitment",
        ShowcaseScenario.STALE_REVISION: "stale_revision",
        ShowcaseScenario.SUBSTITUTION: "substitution",
        ShowcaseScenario.UNRESOLVED_IDENTITY: "unresolved_identity",
        ShowcaseScenario.LIFECYCLE_SUPPRESSED: "quantity_mismatch",
        ShowcaseScenario.LIFECYCLE_REVIEWED: "quantity_mismatch",
        ShowcaseScenario.LIFECYCLE_RESOLVED: "quantity_mismatch",
    }[scenario]
    complete = _coverage("coverage-complete")
    if scenario is ShowcaseScenario.QUALIFIED_MISSING_PO:
        inputs = replace(inputs, coverage=complete)
    elif scenario is ShowcaseScenario.INCOMPLETE_COVERAGE:
        inputs = replace(inputs, coverage=_coverage("coverage-incomplete"))
    elif scenario is ShowcaseScenario.PRICE_DEVIATION:
        inputs = replace(
            inputs,
            planned_price=_price("price-planned"),
            committed_price=_price("price-committed"),
        )
    elif scenario is ShowcaseScenario.LATE_COMMITMENT:
        inputs = replace(
            inputs,
            required_schedule=_schedule("schedule-required", "required_by"),
            commitment=_schedule("schedule-commit", "committed_for"),
        )
    elif scenario is ShowcaseScenario.STALE_REVISION:
        inputs = replace(
            inputs,
            revision=RevisionEvidence(
                "revision-comparison",
                str(_source_record("revision-b")["revision"]),
                str(_source_record("revision-a")["revision"]),
                (str(_source_record("revision-b")["supersedes"]),),
                _ANOMALY_SCOPE,
                _ANOMALY_AS_OF,
                (
                    anomaly_source_evidence("revision-a"),
                    anomaly_source_evidence("revision-b"),
                ),
                supersession_edge_ids=("revision-b-supersedes-a",),
            ),
        )
    elif scenario is ShowcaseScenario.SUBSTITUTION:
        inputs = replace(
            inputs,
            substitution=SubstitutionEvidence(
                "substitution",
                Decimal(str(_source_record("substitution")["quantity"])),
                str(_source_record("substitution")["relationship"]),
                _ANOMALY_SCOPE,
                _ANOMALY_AS_OF,
                (anomaly_source_evidence("substitution"),),
            ),
        )
    elif scenario is ShowcaseScenario.UNRESOLVED_IDENTITY:
        inputs = replace(
            inputs,
            resolution=ResolutionEvidence(
                "identity-unresolved",
                str(_source_record("identity-unresolved")["decision"]),
                str(_source_record("identity-unresolved")["mention"]),
                None,
                _ANOMALY_SCOPE,
                _ANOMALY_AS_OF,
                (anomaly_source_evidence("identity-unresolved"),),
            ),
        )
    else:
        inputs = replace(inputs, ordered_lines=(_line("po-2", "2"),), coverage=complete)

    policies = _anomaly_policies()
    context = replace(
        local_provenance_context(),
        run_id="showcase-anomaly-v1",
        workflow_name="showcase-anomaly-assessment",
        workflow_version="1",
        config_digest=policies.digest,
        input_snapshot_ids=tuple(sorted(ref.evidence_id for ref in _input_evidence(inputs))),
        started_at=_ANOMALY_AS_OF,
    )
    provenance = DecisionProvenance(
        context,
        "full-anomaly-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="procurement-anomaly-assessment/v1",
    )
    assessments = AnomalyService(policies, provenance, _ANOMALY_AS_OF).assess(
        inputs, request_context=request_context
    )
    selected = next(item for item in assessments if item.kind.value == selected_kind)
    if selected.anomaly is None:
        raise SemanticContractError("showcase selection must produce an anomaly")
    history = _lifecycle_history(scenario, selected.anomaly)
    projected = AnomalyService.project_lifecycle(selected.anomaly, history)
    return ShowcaseAnomalyResult(scenario, inputs, assessments, selected, history, projected)


def _coverage(source_id: str) -> CoverageAttestation:
    record = _source_record(source_id)
    return CoverageAttestation(
        source_id,
        "GPU-A",
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        bool(record["complete"]),
        bool(record["current"]),
        bool(record["authoritative"]),
        (anomaly_source_evidence(source_id),),
    )


def _line(source_id: str, quantity: str) -> QualifiedOrderLine:
    return QualifiedOrderLine(
        source_id,
        source_id,
        Decimal(quantity),
        "ea",
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        True,
        (anomaly_source_evidence(source_id),),
    )


def _price(source_id: str) -> PriceEvidence:
    record = _source_record(source_id)
    return PriceEvidence(
        source_id,
        Decimal(str(record["value"])),
        str(record["currency"]),
        str(record["unit"]),
        str(record["basis"]),
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        (anomaly_source_evidence(source_id),),
    )


def _schedule(source_id: str, value_field: str) -> ScheduleEvidence:
    record = _source_record(source_id)
    return ScheduleEvidence(
        source_id,
        date.fromisoformat(str(record[value_field])),
        bool(record.get("confirmed", True)),
        _ANOMALY_SCOPE,
        _ANOMALY_AS_OF,
        (anomaly_source_evidence(source_id),),
    )


def _anomaly_policies() -> AnomalyAssessmentPolicies:
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


def _input_evidence(inputs: AnomalyAssessmentInput) -> tuple[EvidenceRef, ...]:
    values = list(inputs.governance_evidence)
    values.extend(ref for line in inputs.ordered_lines for ref in line.evidence)
    for item in (
        inputs.coverage,
        inputs.planned_price,
        inputs.committed_price,
        inputs.required_schedule,
        inputs.commitment,
        inputs.revision,
        inputs.substitution,
        inputs.resolution,
    ):
        if item is not None:
            values.extend(item.evidence)
    return tuple({ref.evidence_id: ref for ref in values}.values())


def _lifecycle_history(
    scenario: ShowcaseScenario, anomaly: Anomaly
) -> tuple[AnomalyLifecycleEvent, ...]:
    if scenario not in {
        ShowcaseScenario.LIFECYCLE_SUPPRESSED,
        ShowcaseScenario.LIFECYCLE_REVIEWED,
        ShowcaseScenario.LIFECYCLE_RESOLVED,
    }:
        return ()
    payload = json.loads(
        files("procurement_intelligence_lab.examples")
        .joinpath("anomaly_lifecycle_v1.json")
        .read_text()
    )
    history_name = {
        ShowcaseScenario.LIFECYCLE_SUPPRESSED: "suppressed",
        ShowcaseScenario.LIFECYCLE_REVIEWED: "reviewed",
        ShowcaseScenario.LIFECYCLE_RESOLVED: "resolved",
    }[scenario]
    return tuple(_event_from_fixture(item, anomaly) for item in payload["histories"][history_name])


def _event_from_fixture(item: dict[str, object], anomaly: Anomaly) -> AnomalyLifecycleEvent:
    evidence_ids = cast(list[object], item["evidence_ids"])
    return AnomalyLifecycleEvent(
        event_id=str(item["event_id"]),
        anomaly_id=anomaly.anomaly_id,
        scope=anomaly.scope,
        previous_status=AnomalyStatus(str(item["previous_status"])),
        new_status=AnomalyStatus(str(item["new_status"])),
        actor_ref=str(item["actor_ref"]),
        occurred_at=datetime.fromisoformat(str(item["occurred_at"])),
        recorded_at=datetime.fromisoformat(str(item["recorded_at"])),
        reason=str(item["reason"]),
        evidence_ids=tuple(str(value) for value in evidence_ids),
        evidence_kind=LifecycleEvidenceKind(str(item["evidence_kind"])),
        policy_id=str(item["policy_id"]),
        expected_prior_event_id=(
            str(item["expected_prior_event_id"])
            if item["expected_prior_event_id"] is not None
            else None
        ),
    )
