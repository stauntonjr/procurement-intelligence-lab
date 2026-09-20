from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
    QualifiedOrderLine,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import ExpectedRequirement
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

AS_OF = datetime(2026, 9, 19, tzinfo=UTC)
SCOPE = StateScope("tenant", "project", "site", "governed-v1")
EVIDENCE = EvidenceRef("source", "hash", RecordLocation("orders", "line-1"))
CONTEXT = RequestContext(
    "reviewer",
    "tenant",
    "project",
    "site",
    frozenset({Permission.READ_STATE}),
    "identity-test",
)


def _service(tolerance: str, detected_at: datetime = AS_OF) -> AnomalyService:
    policies = AnomalyAssessmentPolicies(
        MissingPurchaseOrderPolicy("missing-po/v1"),
        QuantityMismatchPolicy("same-policy-id", Decimal(tolerance)),
        CoverageGapPolicy("coverage/v1"),
        SubstitutionPolicy("substitution/v1"),
        StaleRevisionPolicy("revision/v1"),
        PriceDeviationPolicy("price/v1"),
        LateCommitmentPolicy("schedule/v1", timedelta(0)),
        UnresolvedIdentityPolicy("identity/v1"),
    )
    provenance = DecisionProvenance(
        local_provenance_context(),
        "full-anomaly-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="procurement-anomaly-assessment/v1",
    )
    return AnomalyService(policies, provenance, detected_at)


def _input() -> AnomalyAssessmentInput:
    expected = ExpectedRequirement("GPU-A", Decimal(4), SCOPE, AS_OF, (EVIDENCE,))
    line = QualifiedOrderLine(
        "line-1",
        "assertion-1",
        Decimal(2),
        "ea",
        SCOPE,
        AS_OF,
        True,
        (EVIDENCE,),
    )
    return AnomalyAssessmentInput(
        "GPU-A",
        SCOPE,
        AS_OF,
        expected,
        governance_decision_ids=("decision-1",),
        ordered_lines=(line,),
    )


def _quantity(service: AnomalyService, inputs: AnomalyAssessmentInput | None = None):
    return next(
        item
        for item in service.assess(inputs or _input(), request_context=CONTEXT)
        if item.kind.value == "quantity_mismatch"
    )


def test_semantic_identity_ignores_detection_wall_clock_but_tracks_policy_configuration() -> None:
    first = _quantity(_service("0", AS_OF))
    later = _quantity(_service("0", AS_OF.replace(hour=13)))
    changed = _quantity(_service("0.5", AS_OF))

    assert first.assessment_id == later.assessment_id
    assert first.anomaly is not None and later.anomaly is not None
    assert first.anomaly.anomaly_id == later.anomaly.anomaly_id
    assert first.policy_id == changed.policy_id == "same-policy-id"
    assert first.policy_digest != changed.policy_digest
    assert first.assessment_id != changed.assessment_id
    assert changed.anomaly is not None
    assert first.anomaly.anomaly_id != changed.anomaly.anomaly_id


def test_semantic_identity_tracks_scope_as_of_evidence_and_governance() -> None:
    baseline = _quantity(_service("0"))
    changed_as_of = _quantity(_service("0"), replace(_input(), as_of=AS_OF.replace(day=20)))
    changed_governance = _quantity(
        _service("0"), replace(_input(), governance_decision_ids=("decision-2",))
    )
    other_evidence = EvidenceRef("source", "other-hash", RecordLocation("orders", "line-1"))
    base_input = _input()
    assert base_input.expected is not None
    changed_evidence = _quantity(
        _service("0"),
        replace(
            base_input,
            expected=replace(base_input.expected, evidence=(other_evidence,)),
        ),
    )

    assert (
        len(
            {
                baseline.assessment_id,
                changed_as_of.assessment_id,
                changed_governance.assessment_id,
                changed_evidence.assessment_id,
            }
        )
        == 4
    )
