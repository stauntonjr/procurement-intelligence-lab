from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

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
    QualifiedOrderLine,
    ScheduleEvidence,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import ExpectedRequirement
from procurement_intelligence_lab.platform.semantics.anomalies import AnomalyStatus
from procurement_intelligence_lab.platform.semantics.anomaly_lifecycle import (
    AnomalyLifecycleEvent,
    LifecycleEvidenceKind,
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

AS_OF = datetime(2026, 9, 19, 12, tzinfo=UTC)
SCOPE = StateScope("tenant", "project", "site", "governed-v1")
CONTEXT = RequestContext(
    "reviewer",
    SCOPE.tenant_id,
    SCOPE.project_id,
    SCOPE.site_id,
    frozenset({Permission.READ_STATE}),
    "issue-60-regression",
)


def _evidence(source_id: str) -> EvidenceRef:
    return EvidenceRef(
        f"issue-60:{source_id}",
        f"sha256:{source_id}",
        RecordLocation("issue-60-regression", source_id),
    )


def _policies() -> AnomalyAssessmentPolicies:
    return AnomalyAssessmentPolicies(
        MissingPurchaseOrderPolicy("missing-po/v1"),
        QuantityMismatchPolicy("quantity/v1"),
        CoverageGapPolicy("coverage/v1"),
        SubstitutionPolicy("substitution/v1"),
        StaleRevisionPolicy("revision/v1"),
        PriceDeviationPolicy("price/v1"),
        LateCommitmentPolicy("schedule/v1"),
        UnresolvedIdentityPolicy("identity/v1"),
    )


def _service() -> AnomalyService:
    provenance = DecisionProvenance(
        replace(
            local_provenance_context(),
            workflow_name="issue-60-regression",
            input_snapshot_ids=(),
        ),
        "qualified-anomaly-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="synthetic-anomaly-policy/v1",
    )
    return AnomalyService(_policies(), provenance, AS_OF)


def _expected() -> ExpectedRequirement:
    return ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, (_evidence("requirement"),))


def _coverage() -> CoverageAttestation:
    return CoverageAttestation(
        "coverage",
        "GPU-A",
        SCOPE,
        AS_OF,
        complete=True,
        current=True,
        authoritative=True,
        evidence=(_evidence("coverage"),),
    )


def _line(assertion_id: str, quantity: str, *, as_of: datetime = AS_OF) -> QualifiedOrderLine:
    return QualifiedOrderLine(
        "po-line-1",
        assertion_id,
        Decimal(quantity),
        "ea",
        SCOPE,
        as_of,
        True,
        (_evidence(assertion_id),),
    )


def _quantity_input(*lines: QualifiedOrderLine) -> AnomalyAssessmentInput:
    return AnomalyAssessmentInput(
        "GPU-A",
        SCOPE,
        AS_OF,
        _expected(),
        governance_decision_ids=("decision-required-4",),
        governance_evidence=(_evidence("governance"),),
        ordered_lines=lines,
        coverage=_coverage(),
    )


def _result(inputs: AnomalyAssessmentInput, kind: str):
    return next(
        item
        for item in _service().assess(inputs, request_context=CONTEXT)
        if item.kind.value == kind
    )


@pytest.mark.regression
def test_competing_assertions_for_one_po_line_abstain() -> None:
    competing = _result(
        _quantity_input(_line("assertion-a", "2"), _line("assertion-b", "2")),
        "quantity_mismatch",
    )
    assert competing.status is AssessmentStatus.NOT_ASSESSED
    assert competing.reason is AssessmentReason.CONFLICTING_INPUT
    assert dict(competing.input_dispositions) == {
        "assertion-a": "conflicting_version",
        "assertion-b": "conflicting_version",
    }


@pytest.mark.regression
def test_future_assertion_cannot_enter_total_through_shared_po_line_id() -> None:
    current = _line("assertion-current", "2")
    future = _line("assertion-future", "100", as_of=AS_OF + timedelta(days=1))
    qualified = _result(_quantity_input(future, current), "quantity_mismatch")
    assert qualified.status is AssessmentStatus.ANOMALY
    assert qualified.anomaly is not None
    assert qualified.anomaly.observed == Decimal(2)
    assert dict(qualified.input_dispositions) == {
        "assertion-current": "eligible",
        "assertion-future": "rejected_future",
    }


@pytest.mark.regression
def test_changed_assessment_context_cannot_inherit_lifecycle_history() -> None:
    original = _result(_quantity_input(_line("assertion-current", "2")), "quantity_mismatch")
    assert original.anomaly is not None

    changed_as_of_input = replace(
        _quantity_input(_line("assertion-current", "2")),
        as_of=AS_OF + timedelta(hours=1),
    )
    changed_decision_input = replace(
        _quantity_input(_line("assertion-current", "2")),
        governance_decision_ids=("decision-required-4-corrected",),
    )
    changed_as_of = _result(changed_as_of_input, "quantity_mismatch")
    changed_decision = _result(changed_decision_input, "quantity_mismatch")
    assert changed_as_of.anomaly is not None
    assert changed_decision.anomaly is not None
    assert (
        len(
            {
                original.anomaly.anomaly_id,
                changed_as_of.anomaly.anomaly_id,
                changed_decision.anomaly.anomaly_id,
            }
        )
        == 3
    )

    suppression = AnomalyLifecycleEvent(
        "suppress-original",
        original.anomaly.anomaly_id,
        SCOPE,
        AnomalyStatus.OPEN,
        AnomalyStatus.SUPPRESSED,
        "reviewer:synthetic",
        AS_OF + timedelta(minutes=1),
        AS_OF + timedelta(minutes=2),
        "bounded suppression for the original assessment",
        ("suppression-evidence",),
        LifecycleEvidenceKind.SUPPRESSION,
        "anomaly-lifecycle/v1",
        None,
    )
    with pytest.raises(ValueError, match="different anomaly"):
        AnomalyService.project_lifecycle(changed_as_of.anomaly, (suppression,))
    with pytest.raises(ValueError, match="different anomaly"):
        AnomalyService.project_lifecycle(changed_decision.anomaly, (suppression,))


@pytest.mark.regression
def test_superseded_required_schedule_cannot_drive_late_commitment() -> None:
    required = ScheduleEvidence(
        "required-obsolete",
        date(2026, 10, 1),
        True,
        SCOPE,
        AS_OF,
        (_evidence("required-obsolete"),),
        superseded=True,
    )
    commitment = ScheduleEvidence(
        "commitment-current",
        date(2026, 10, 3),
        True,
        SCOPE,
        AS_OF,
        (_evidence("commitment-current"),),
    )
    result = _result(
        AnomalyAssessmentInput(
            "GPU-A",
            SCOPE,
            AS_OF,
            None,
            governance_decision_ids=("decision-schedule",),
            governance_evidence=(_evidence("schedule-governance"),),
            required_schedule=required,
            commitment=commitment,
        ),
        "late_commitment",
    )
    assert result.status is AssessmentStatus.NOT_ASSESSED
    assert result.reason is AssessmentReason.STALE_INPUT
    assert result.input_ids == ("required-obsolete",)
