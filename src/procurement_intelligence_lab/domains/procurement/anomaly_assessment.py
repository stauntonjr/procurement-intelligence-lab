"""Qualified, evidence-backed procurement anomaly assessment."""

import json
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from procurement_intelligence_lab.domains.procurement.anomalies import (
    AnomalyKind,
    CoverageGapDetails,
    CoverageGapPolicy,
    LateCommitmentPolicy,
    MissingPurchaseOrderDetails,
    MissingPurchaseOrderPolicy,
    PriceDeviationPolicy,
    QuantityMismatchPolicy,
    StaleRevisionPolicy,
    SubstitutionDetails,
    SubstitutionPolicy,
    UnresolvedIdentityPolicy,
    detect_late_commitment,
    detect_price_deviation,
    detect_quantity_mismatch,
    detect_stale_revision,
    detect_unresolved_identity,
)
from procurement_intelligence_lab.domains.procurement.state import ExpectedRequirement
from procurement_intelligence_lab.platform.semantics.anomalies import (
    Anomaly,
    AnomalyDetails,
    AnomalySeverity,
    AnomalyStatus,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ScopeContractError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class AssessmentStatus(StrEnum):
    ANOMALY = "anomaly"
    CLEAR = "clear"
    NOT_ASSESSED = "not_assessed"
    NOT_APPLICABLE = "not_applicable"


class AssessmentReason(StrEnum):
    MISSING_OBSERVATION = "missing_observation"
    UNRESOLVED_REQUIREMENT = "unresolved_requirement"
    MISSING_COVERAGE = "missing_coverage"
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    CONFLICTING_INPUT = "conflicting_input"
    SCOPE_MISMATCH = "scope_mismatch"
    FUTURE_INPUT = "future_input"
    INCOMPATIBLE_UNIT = "incompatible_unit"
    INELIGIBLE_INPUT = "ineligible_input"
    MISSING_PRICE = "missing_price"
    INCOMPATIBLE_BASIS = "incompatible_basis"
    MISSING_SCHEDULE = "missing_schedule"
    MISSING_CONFIRMATION = "missing_confirmation"
    MISSING_SUPERSESSION = "missing_supersession"
    MISSING_RELATIONSHIP = "missing_relationship"
    MISSING_RESOLUTION = "missing_resolution"
    STALE_INPUT = "stale_input"


@dataclass(frozen=True)
class CoverageAttestation:
    attestation_id: str
    subject_key: str
    scope: StateScope
    as_of: datetime
    complete: bool
    current: bool
    authoritative: bool
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.attestation_id.strip() or not self.subject_key.strip():
            raise SemanticContractError("coverage identity and subject are required")
        _require_aware("coverage as_of", self.as_of)
        _require_evidence("coverage", self.evidence)

    @property
    def qualified_complete(self) -> bool:
        return self.complete and self.current and self.authoritative


@dataclass(frozen=True)
class QualifiedOrderLine:
    line_id: str
    assertion_id: str
    quantity: Decimal
    unit: str
    scope: StateScope
    as_of: datetime
    approved: bool
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.line_id.strip() or not self.assertion_id.strip() or not self.unit.strip():
            raise SemanticContractError("order line identity, assertion, and unit are required")
        if not self.quantity.is_finite() or self.quantity < Decimal(0):
            raise SemanticContractError("ordered quantity must be finite and non-negative")
        _require_aware("order line as_of", self.as_of)
        _require_evidence("order line", self.evidence)

    @property
    def replay_identity(self) -> tuple[object, ...]:
        return (
            self.assertion_id,
            self.quantity,
            self.unit,
            self.scope,
            self.as_of,
            self.approved,
            tuple(sorted(ref.evidence_id for ref in self.evidence)),
        )


@dataclass(frozen=True)
class PriceEvidence:
    input_id: str
    value: Decimal
    currency: str
    unit: str
    basis: str
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    current: bool = True
    conflicted: bool = False

    def __post_init__(self) -> None:
        if not all(item.strip() for item in (self.input_id, self.currency, self.unit, self.basis)):
            raise SemanticContractError("price identity, currency, unit, and basis are required")
        if not self.value.is_finite() or self.value < Decimal(0):
            raise SemanticContractError("price must be finite and non-negative")
        _require_aware("price as_of", self.as_of)
        _require_evidence("price", self.evidence)


@dataclass(frozen=True)
class ScheduleEvidence:
    input_id: str
    value: date
    confirmed: bool
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    superseded: bool = False
    conflicted: bool = False

    def __post_init__(self) -> None:
        if not self.input_id.strip():
            raise SemanticContractError("schedule identity is required")
        _require_aware("schedule as_of", self.as_of)
        _require_evidence("schedule", self.evidence)


@dataclass(frozen=True)
class RevisionEvidence:
    input_id: str
    expected_revision: str
    observed_revision: str
    superseded_revision_ids: tuple[str, ...]
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    supersession_edge_ids: tuple[str, ...] = ()
    authoritative: bool = True
    ambiguous: bool = False

    def __post_init__(self) -> None:
        if not all(
            item.strip() for item in (self.input_id, self.expected_revision, self.observed_revision)
        ):
            raise SemanticContractError("revision identity and labels are required")
        if any(not item.strip() for item in self.superseded_revision_ids):
            raise SemanticContractError("superseded revision IDs must not be blank")
        if any(not item.strip() for item in self.supersession_edge_ids):
            raise SemanticContractError("supersession edge IDs must not be blank")
        _require_aware("revision as_of", self.as_of)
        _require_evidence("revision", self.evidence)


@dataclass(frozen=True)
class SubstitutionEvidence:
    input_id: str
    quantity: Decimal
    relationship_kind: str
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]
    approved: bool = True
    ambiguous: bool = False

    def __post_init__(self) -> None:
        if not self.input_id.strip() or not self.relationship_kind.strip():
            raise SemanticContractError("substitution identity and relationship are required")
        if not self.quantity.is_finite() or self.quantity < Decimal(0):
            raise SemanticContractError("substitution quantity must be finite and non-negative")
        _require_aware("substitution as_of", self.as_of)
        _require_evidence("substitution", self.evidence)


@dataclass(frozen=True)
class ResolutionEvidence:
    decision_id: str
    status: str
    mention: str
    canonical_key: str | None
    scope: StateScope
    as_of: datetime
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.decision_id.strip() or not self.mention.strip():
            raise SemanticContractError("resolution decision and mention are required")
        if self.status not in {"resolved", "unresolved", "ambiguous"}:
            raise SemanticContractError("resolution status is unsupported")
        if self.status == "resolved" and not (self.canonical_key and self.canonical_key.strip()):
            raise SemanticContractError("resolved identity requires a canonical key")
        if self.status != "resolved" and self.canonical_key is not None:
            raise SemanticContractError("unresolved identity cannot carry a canonical key")
        _require_aware("resolution as_of", self.as_of)
        _require_evidence("resolution", self.evidence)


@dataclass(frozen=True)
class QuantityAssessmentPolicies:
    missing_purchase_order: MissingPurchaseOrderPolicy
    quantity_mismatch: QuantityMismatchPolicy
    coverage_gap: CoverageGapPolicy

    @property
    def canonical_configuration(self) -> str:
        payload = {
            "coverage_gap": {
                "flag_non_current": self.coverage_gap.flag_non_current,
                "policy_id": self.coverage_gap.policy_id,
                "unknown_quantity_tolerance": str(self.coverage_gap.unknown_quantity_tolerance),
            },
            "missing_purchase_order": {
                "minimum_required_quantity": str(
                    self.missing_purchase_order.minimum_required_quantity
                ),
                "policy_id": self.missing_purchase_order.policy_id,
            },
            "quantity_mismatch": {
                "policy_id": self.quantity_mismatch.policy_id,
                "tolerance": str(self.quantity_mismatch.tolerance),
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @property
    def digest(self) -> str:
        return sha256(self.canonical_configuration.encode()).hexdigest()


@dataclass(frozen=True)
class AnomalyAssessmentPolicies(QuantityAssessmentPolicies):
    substitution: SubstitutionPolicy
    stale_revision: StaleRevisionPolicy
    price_deviation: PriceDeviationPolicy
    late_commitment: LateCommitmentPolicy
    unresolved_identity: UnresolvedIdentityPolicy

    @property
    def canonical_configuration(self) -> str:
        payload = json.loads(super().canonical_configuration)
        payload.update(
            {
                "late_commitment": {
                    "policy_id": self.late_commitment.policy_id,
                    "tolerance_seconds": str(self.late_commitment.tolerance.total_seconds()),
                },
                "price_deviation": {
                    "policy_id": self.price_deviation.policy_id,
                    "tolerance": str(self.price_deviation.tolerance),
                },
                "stale_revision": {"policy_id": self.stale_revision.policy_id},
                "substitution": {
                    "policy_id": self.substitution.policy_id,
                    "tolerance": str(self.substitution.tolerance),
                },
                "unresolved_identity": {"policy_id": self.unresolved_identity.policy_id},
            }
        )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class AnomalyAssessmentInput:
    subject_key: str
    scope: StateScope
    as_of: datetime
    expected: ExpectedRequirement | None
    expected_unit: str = "ea"
    governance_decision_ids: tuple[str, ...] = ()
    governance_evidence: tuple[EvidenceRef, ...] = ()
    ordered_lines: tuple[QualifiedOrderLine, ...] = ()
    coverage: CoverageAttestation | None = None
    planned_price: PriceEvidence | None = None
    committed_price: PriceEvidence | None = None
    required_schedule: ScheduleEvidence | None = None
    commitment: ScheduleEvidence | None = None
    revision: RevisionEvidence | None = None
    substitution: SubstitutionEvidence | None = None
    resolution: ResolutionEvidence | None = None

    def __post_init__(self) -> None:
        if not self.subject_key.strip() or not self.expected_unit.strip():
            raise SemanticContractError("assessment subject and expected unit are required")
        _require_aware("assessment as_of", self.as_of)
        if any(not item.strip() for item in self.governance_decision_ids):
            raise SemanticContractError("governance decision IDs must not be blank")
        if self.expected is not None:
            if not self.governance_decision_ids or not self.governance_evidence:
                raise SemanticContractError(
                    "expected requirement requires governance decision and evidence"
                )
            if self.expected.canonical_key != self.subject_key:
                raise SemanticContractError("expected requirement subject must match assessment")
            if self.expected.scope != self.scope:
                raise ScopeContractError("expected requirement scope must match assessment")
            if self.expected.as_of > self.as_of:
                raise TemporalContractError("expected requirement cannot be future-dated")


@dataclass(frozen=True)
class AnomalyAssessment:
    subject_key: str
    kind: AnomalyKind
    status: AssessmentStatus
    reason: AssessmentReason | None
    anomaly: Anomaly | None
    input_ids: tuple[str, ...]
    decision_ids: tuple[str, ...]
    input_dispositions: tuple[tuple[str, str], ...]
    evidence_by_role: tuple[tuple[str, tuple[EvidenceRef, ...]], ...]
    policy_id: str
    policy_configuration: str
    policy_digest: str
    scope: StateScope
    as_of: datetime

    def __post_init__(self) -> None:
        if not self.subject_key.strip():
            raise SemanticContractError("anomaly assessment subject is required")
        if self.status is AssessmentStatus.ANOMALY and self.anomaly is None:
            raise SemanticContractError("anomaly assessment status requires an anomaly")
        if self.status is not AssessmentStatus.ANOMALY and self.anomaly is not None:
            raise SemanticContractError("only anomaly assessments may carry an anomaly")
        if self.status is AssessmentStatus.NOT_ASSESSED and self.reason is None:
            raise SemanticContractError("not-assessed results require a reason")
        if self.status is not AssessmentStatus.NOT_ASSESSED and self.reason is not None:
            raise SemanticContractError("only not-assessed results carry a reason")

    @property
    def evidence(self) -> tuple[EvidenceRef, ...]:
        by_id = {
            ref.evidence_id: ref for _, references in self.evidence_by_role for ref in references
        }
        return tuple(by_id[key] for key in sorted(by_id))

    @property
    def assessment_id(self) -> str:
        return stable_id(
            "anomaly-assessment",
            self.subject_key,
            self.kind.value,
            self.status.value,
            self.reason.value if self.reason else None,
            self.anomaly.anomaly_id if self.anomaly else None,
            tuple(sorted(self.input_ids)),
            tuple(sorted(self.decision_ids)),
            tuple(ref.evidence_id for ref in self.evidence),
            self.policy_digest,
            self.scope,
            self.as_of.isoformat(),
        )


def assess_quantity(
    inputs: AnomalyAssessmentInput,
    *,
    policy: QuantityAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> tuple[AnomalyAssessment, ...]:
    """Assess missing PO, quantity mismatch, and coverage with explicit qualifications."""
    _require_aware("detected_at", detected_at)
    evidence_roles = _roles_for(
        _evidence_roles(inputs), "requirement", "governance", "observation", "coverage"
    )
    invalid_reason, lines = _admit_lines(inputs)
    missing = _assess_missing_po(
        inputs,
        lines,
        invalid_reason,
        evidence_roles,
        policy,
        _assessment_provenance(inputs, provenance, policy, AnomalyKind.MISSING_PO, evidence_roles),
        detected_at,
    )
    quantity = _assess_quantity_mismatch(
        inputs,
        lines,
        invalid_reason,
        evidence_roles,
        policy,
        _assessment_provenance(
            inputs, provenance, policy, AnomalyKind.QUANTITY_MISMATCH, evidence_roles
        ),
        detected_at,
    )
    coverage = _assess_coverage(
        inputs,
        evidence_roles,
        policy,
        _assessment_provenance(
            inputs, provenance, policy, AnomalyKind.COVERAGE_GAP, evidence_roles
        ),
        detected_at,
    )
    return missing, quantity, coverage


def assess_anomalies(
    inputs: AnomalyAssessmentInput,
    *,
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> tuple[AnomalyAssessment, ...]:
    """Assess all eight procurement anomaly kinds independently."""
    quantity = assess_quantity(
        inputs,
        policy=policies,
        provenance=provenance,
        detected_at=detected_at,
    )
    evidence_roles = _evidence_roles(inputs)
    substitution_roles = _roles_for(evidence_roles, "relationship", "governance")
    revision_roles = _roles_for(evidence_roles, "supersession", "governance")
    price_roles = _roles_for(evidence_roles, "planned_price", "committed_price", "governance")
    schedule_roles = _roles_for(evidence_roles, "required_schedule", "commitment", "governance")
    identity_roles = _roles_for(evidence_roles, "resolution", "governance")
    return quantity + (
        _assess_substitution(
            inputs,
            substitution_roles,
            policies,
            _assessment_provenance(
                inputs, provenance, policies, AnomalyKind.SUBSTITUTION, substitution_roles
            ),
            detected_at,
        ),
        _assess_revision(
            inputs,
            revision_roles,
            policies,
            _assessment_provenance(
                inputs, provenance, policies, AnomalyKind.STALE_REVISION, revision_roles
            ),
            detected_at,
        ),
        _assess_price(
            inputs,
            price_roles,
            policies,
            _assessment_provenance(
                inputs, provenance, policies, AnomalyKind.PRICE_DEVIATION, price_roles
            ),
            detected_at,
        ),
        _assess_schedule(
            inputs,
            schedule_roles,
            policies,
            _assessment_provenance(
                inputs, provenance, policies, AnomalyKind.LATE_COMMITMENT, schedule_roles
            ),
            detected_at,
        ),
        _assess_identity(
            inputs,
            identity_roles,
            policies,
            _assessment_provenance(
                inputs, provenance, policies, AnomalyKind.UNRESOLVED_IDENTITY, identity_roles
            ),
            detected_at,
        ),
    )


def _assess_substitution(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.SUBSTITUTION
    value = inputs.substitution
    if value is None or value.relationship_kind != "substitute":
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_RELATIONSHIP,
            None,
            (),
            evidence_roles,
            policies.substitution.policy_id,
            policies,
        )
    if value.ambiguous:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.CONFLICTING_INPUT,
            None,
            (value.input_id,),
            evidence_roles,
            policies.substitution.policy_id,
            policies,
        )
    if not value.approved:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.INELIGIBLE_INPUT,
            None,
            (value.input_id,),
            evidence_roles,
            policies.substitution.policy_id,
            policies,
        )
    reason = _qualified_input_reason(inputs, value.scope, value.as_of)
    if reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            reason,
            None,
            (value.input_id,),
            evidence_roles,
            policies.substitution.policy_id,
            policies,
        )
    if value.quantity <= policies.substitution.tolerance:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (value.input_id,),
            evidence_roles,
            policies.substitution.policy_id,
            policies,
        )
    anomaly = _make_anomaly(
        inputs,
        SubstitutionDetails(Decimal(0), value.quantity),
        AnomalySeverity.WARNING,
        evidence_roles,
        policies.substitution.policy_id,
        provenance,
        detected_at,
    )
    return _result(
        inputs,
        kind,
        AssessmentStatus.ANOMALY,
        None,
        anomaly,
        (value.input_id,),
        evidence_roles,
        policies.substitution.policy_id,
        policies,
    )


def _assess_revision(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.STALE_REVISION
    value = inputs.revision
    if value is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_SUPERSESSION,
            None,
            (),
            evidence_roles,
            policies.stale_revision.policy_id,
            policies,
        )
    reason = _qualified_input_reason(inputs, value.scope, value.as_of)
    if reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            reason,
            None,
            (value.input_id,),
            evidence_roles,
            policies.stale_revision.policy_id,
            policies,
        )
    if value.expected_revision == value.observed_revision:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (value.input_id,),
            evidence_roles,
            policies.stale_revision.policy_id,
            policies,
        )
    if value.ambiguous:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.CONFLICTING_INPUT,
            None,
            (value.input_id,),
            evidence_roles,
            policies.stale_revision.policy_id,
            policies,
        )
    is_superseded = value.observed_revision in value.superseded_revision_ids
    if not is_superseded or not value.authoritative or not value.supersession_edge_ids:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_SUPERSESSION,
            None,
            (value.input_id,),
            evidence_roles,
            policies.stale_revision.policy_id,
            policies,
        )
    anomaly = detect_stale_revision(
        inputs.subject_key,
        value.expected_revision,
        value.observed_revision,
        _flatten_evidence(evidence_roles),
        is_superseded=True,
        policy=policies.stale_revision,
        provenance=provenance,
        detected_at=detected_at,
        scope=inputs.scope,
    )
    return _result(
        inputs,
        kind,
        AssessmentStatus.ANOMALY,
        None,
        anomaly,
        (value.input_id,),
        evidence_roles,
        policies.stale_revision.policy_id,
        policies,
    )


def _assess_price(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.PRICE_DEVIATION
    planned, committed = inputs.planned_price, inputs.committed_price
    if planned is None or committed is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_PRICE,
            None,
            (),
            evidence_roles,
            policies.price_deviation.policy_id,
            policies,
        )
    for value in (planned, committed):
        reason = _qualified_input_reason(inputs, value.scope, value.as_of)
        if reason is not None:
            return _result(
                inputs,
                kind,
                AssessmentStatus.NOT_ASSESSED,
                reason,
                None,
                (value.input_id,),
                evidence_roles,
                policies.price_deviation.policy_id,
                policies,
            )
    if not planned.current or not committed.current:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.STALE_INPUT,
            None,
            (planned.input_id, committed.input_id),
            evidence_roles,
            policies.price_deviation.policy_id,
            policies,
        )
    if planned.conflicted or committed.conflicted:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.CONFLICTING_INPUT,
            None,
            (planned.input_id, committed.input_id),
            evidence_roles,
            policies.price_deviation.policy_id,
            policies,
        )
    if (planned.currency, planned.unit, planned.basis) != (
        committed.currency,
        committed.unit,
        committed.basis,
    ):
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.INCOMPATIBLE_BASIS,
            None,
            (planned.input_id, committed.input_id),
            evidence_roles,
            policies.price_deviation.policy_id,
            policies,
        )
    anomaly = detect_price_deviation(
        inputs.subject_key,
        planned.value,
        committed.value,
        _flatten_evidence(evidence_roles),
        policy=policies.price_deviation,
        provenance=provenance,
        detected_at=detected_at,
        scope=inputs.scope,
    )
    status = AssessmentStatus.ANOMALY if anomaly else AssessmentStatus.CLEAR
    return _result(
        inputs,
        kind,
        status,
        None,
        anomaly,
        (planned.input_id, committed.input_id),
        evidence_roles,
        policies.price_deviation.policy_id,
        policies,
    )


def _assess_schedule(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.LATE_COMMITMENT
    required, commitment = inputs.required_schedule, inputs.commitment
    if required is None or commitment is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_SCHEDULE,
            None,
            (),
            evidence_roles,
            policies.late_commitment.policy_id,
            policies,
        )
    if not commitment.confirmed:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_CONFIRMATION,
            None,
            (commitment.input_id,),
            evidence_roles,
            policies.late_commitment.policy_id,
            policies,
        )
    if required.conflicted or commitment.conflicted:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.CONFLICTING_INPUT,
            None,
            (required.input_id, commitment.input_id),
            evidence_roles,
            policies.late_commitment.policy_id,
            policies,
        )
    superseded_input_ids = tuple(
        value.input_id for value in (required, commitment) if value.superseded
    )
    if superseded_input_ids:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.STALE_INPUT,
            None,
            superseded_input_ids,
            evidence_roles,
            policies.late_commitment.policy_id,
            policies,
        )
    for value in (required, commitment):
        reason = _qualified_input_reason(inputs, value.scope, value.as_of)
        if reason is not None:
            return _result(
                inputs,
                kind,
                AssessmentStatus.NOT_ASSESSED,
                reason,
                None,
                (value.input_id,),
                evidence_roles,
                policies.late_commitment.policy_id,
                policies,
            )
    anomaly = detect_late_commitment(
        inputs.subject_key,
        required.value,
        commitment.value,
        _flatten_evidence(evidence_roles),
        policy=policies.late_commitment,
        provenance=provenance,
        detected_at=detected_at,
        scope=inputs.scope,
    )
    status = AssessmentStatus.ANOMALY if anomaly else AssessmentStatus.CLEAR
    return _result(
        inputs,
        kind,
        status,
        None,
        anomaly,
        (required.input_id, commitment.input_id),
        evidence_roles,
        policies.late_commitment.policy_id,
        policies,
    )


def _assess_identity(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policies: AnomalyAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.UNRESOLVED_IDENTITY
    value = inputs.resolution
    if value is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_RESOLUTION,
            None,
            (),
            evidence_roles,
            policies.unresolved_identity.policy_id,
            policies,
        )
    reason = _qualified_input_reason(inputs, value.scope, value.as_of)
    if reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            reason,
            None,
            (value.decision_id,),
            evidence_roles,
            policies.unresolved_identity.policy_id,
            policies,
        )
    if value.status == "resolved":
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (value.decision_id,),
            evidence_roles,
            policies.unresolved_identity.policy_id,
            policies,
        )
    anomaly = detect_unresolved_identity(
        inputs.subject_key,
        value.mention,
        _flatten_evidence(evidence_roles),
        expected=None,
        policy=policies.unresolved_identity,
        provenance=provenance,
        detected_at=detected_at,
        scope=inputs.scope,
    )
    return _result(
        inputs,
        kind,
        AssessmentStatus.ANOMALY,
        None,
        anomaly,
        (value.decision_id,),
        evidence_roles,
        policies.unresolved_identity.policy_id,
        policies,
    )


def _assess_missing_po(
    inputs: AnomalyAssessmentInput,
    lines: tuple[QualifiedOrderLine, ...],
    invalid_reason: AssessmentReason | None,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policy: QuantityAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.MISSING_PO
    if inputs.expected is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.UNRESOLVED_REQUIREMENT,
            None,
            (),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    if invalid_reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            invalid_reason,
            None,
            tuple(line.line_id for line in inputs.ordered_lines),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    if inputs.coverage is None:
        reason = (
            AssessmentReason.MISSING_COVERAGE if lines else AssessmentReason.MISSING_OBSERVATION
        )
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            reason,
            None,
            tuple(line.line_id for line in lines),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    coverage_reason = _coverage_rejection(inputs, inputs.coverage)
    if coverage_reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            coverage_reason,
            None,
            (inputs.coverage.attestation_id,),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    if not inputs.coverage.qualified_complete:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.INCOMPLETE_COVERAGE,
            None,
            (inputs.coverage.attestation_id,),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    if lines:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            tuple(line.line_id for line in lines),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    expected = inputs.expected.required_quantity
    if expected <= policy.missing_purchase_order.minimum_required_quantity:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (inputs.coverage.attestation_id,),
            evidence_roles,
            policy.missing_purchase_order.policy_id,
            policy,
        )
    anomaly = _make_anomaly(
        inputs,
        MissingPurchaseOrderDetails(expected, None),
        AnomalySeverity.WARNING,
        evidence_roles,
        policy.missing_purchase_order.policy_id,
        provenance,
        detected_at,
    )
    return _result(
        inputs,
        kind,
        AssessmentStatus.ANOMALY,
        None,
        anomaly,
        (inputs.coverage.attestation_id,),
        evidence_roles,
        policy.missing_purchase_order.policy_id,
        policy,
    )


def _assess_quantity_mismatch(
    inputs: AnomalyAssessmentInput,
    lines: tuple[QualifiedOrderLine, ...],
    invalid_reason: AssessmentReason | None,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policy: QuantityAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.QUANTITY_MISMATCH
    if inputs.expected is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.UNRESOLVED_REQUIREMENT,
            None,
            (),
            evidence_roles,
            policy.quantity_mismatch.policy_id,
            policy,
        )
    if invalid_reason is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            invalid_reason,
            None,
            tuple(line.line_id for line in inputs.ordered_lines),
            evidence_roles,
            policy.quantity_mismatch.policy_id,
            policy,
        )
    if inputs.coverage is not None:
        coverage_reason = _coverage_rejection(inputs, inputs.coverage)
        if coverage_reason is not None:
            return _result(
                inputs,
                kind,
                AssessmentStatus.NOT_ASSESSED,
                coverage_reason,
                None,
                (inputs.coverage.attestation_id,),
                evidence_roles,
                policy.quantity_mismatch.policy_id,
                policy,
            )
    if inputs.coverage is not None and not inputs.coverage.qualified_complete:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.INCOMPLETE_COVERAGE,
            None,
            tuple(line.line_id for line in lines),
            evidence_roles,
            policy.quantity_mismatch.policy_id,
            policy,
        )
    if not lines and inputs.coverage is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_OBSERVATION,
            None,
            (),
            evidence_roles,
            policy.quantity_mismatch.policy_id,
            policy,
        )
    if any(line.unit != inputs.expected_unit for line in lines):
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.INCOMPATIBLE_UNIT,
            None,
            tuple(line.line_id for line in lines),
            evidence_roles,
            policy.quantity_mismatch.policy_id,
            policy,
        )
    observed = sum((line.quantity for line in lines), Decimal(0))
    anomaly = detect_quantity_mismatch(
        inputs.subject_key,
        inputs.expected.required_quantity,
        observed,
        _flatten_evidence(evidence_roles),
        policy=policy.quantity_mismatch,
        provenance=provenance,
        detected_at=detected_at,
        scope=inputs.scope,
    )
    status = AssessmentStatus.ANOMALY if anomaly else AssessmentStatus.CLEAR
    input_ids = tuple(line.line_id for line in lines)
    if not input_ids and inputs.coverage is not None:
        input_ids = (inputs.coverage.attestation_id,)
    return _result(
        inputs,
        kind,
        status,
        None,
        anomaly,
        input_ids,
        evidence_roles,
        policy.quantity_mismatch.policy_id,
        policy,
    )


def _assess_coverage(
    inputs: AnomalyAssessmentInput,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policy: QuantityAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyAssessment:
    kind = AnomalyKind.COVERAGE_GAP
    coverage = inputs.coverage
    if coverage is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.MISSING_COVERAGE,
            None,
            (),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    rejection = _coverage_rejection(inputs, coverage)
    if rejection is not None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            rejection,
            None,
            (coverage.attestation_id,),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    if coverage.qualified_complete:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (coverage.attestation_id,),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    if coverage.complete and coverage.authoritative and not policy.coverage_gap.flag_non_current:
        return _result(
            inputs,
            kind,
            AssessmentStatus.CLEAR,
            None,
            None,
            (coverage.attestation_id,),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    if inputs.expected is None:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.UNRESOLVED_REQUIREMENT,
            None,
            (coverage.attestation_id,),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    anomaly = _make_anomaly(
        inputs,
        CoverageGapDetails(inputs.expected.required_quantity, Decimal(0)),
        AnomalySeverity.INFO,
        evidence_roles,
        policy.coverage_gap.policy_id,
        provenance,
        detected_at,
    )
    return _result(
        inputs,
        kind,
        AssessmentStatus.ANOMALY,
        None,
        anomaly,
        (coverage.attestation_id,),
        evidence_roles,
        policy.coverage_gap.policy_id,
        policy,
    )


def _admit_lines(
    inputs: AnomalyAssessmentInput,
) -> tuple[AssessmentReason | None, tuple[QualifiedOrderLine, ...]]:
    dispositions = dict(_input_dispositions(inputs))
    if "conflicting_version" in set(dispositions.values()):
        return AssessmentReason.CONFLICTING_INPUT, ()
    eligible = {
        line.assertion_id: line
        for line in inputs.ordered_lines
        if dispositions[line.assertion_id] == "eligible"
    }
    return None, tuple(
        sorted(eligible.values(), key=lambda item: (item.line_id, item.assertion_id))
    )


def _coverage_rejection(
    inputs: AnomalyAssessmentInput, coverage: CoverageAttestation
) -> AssessmentReason | None:
    if coverage.subject_key != inputs.subject_key or coverage.scope != inputs.scope:
        return AssessmentReason.SCOPE_MISMATCH
    if coverage.as_of > inputs.as_of:
        return AssessmentReason.FUTURE_INPUT
    return None


def _input_dispositions(inputs: AnomalyAssessmentInput) -> tuple[tuple[str, str], ...]:
    dispositions: dict[str, str] = {}
    grouped_assertions: dict[str, list[QualifiedOrderLine]] = {}
    for line in inputs.ordered_lines:
        grouped_assertions.setdefault(line.assertion_id, []).append(line)

    eligible_by_line: dict[str, list[QualifiedOrderLine]] = {}
    for assertion_id, assertion_lines in sorted(grouped_assertions.items()):
        versions = {line.replay_identity for line in assertion_lines}
        if len(versions) != 1:
            dispositions[assertion_id] = "conflicting_version"
            continue
        line = min(
            assertion_lines,
            key=lambda item: (item.line_id, item.evidence[0].evidence_id),
        )
        if line.scope != inputs.scope:
            dispositions[assertion_id] = "rejected_scope"
            continue
        if line.as_of > inputs.as_of:
            dispositions[assertion_id] = "rejected_future"
            continue
        if not line.approved:
            dispositions[assertion_id] = "rejected_ineligible"
            continue
        dispositions[assertion_id] = "eligible"
        eligible_by_line.setdefault(line.line_id, []).append(line)

    for line_versions in eligible_by_line.values():
        if len(line_versions) > 1:
            for line in line_versions:
                dispositions[line.assertion_id] = "conflicting_version"
    return tuple(sorted(dispositions.items()))


def _evidence_roles(
    inputs: AnomalyAssessmentInput,
) -> tuple[tuple[str, tuple[EvidenceRef, ...]], ...]:
    roles: list[tuple[str, tuple[EvidenceRef, ...]]] = []
    if inputs.expected is not None:
        roles.append(("requirement", inputs.expected.evidence))
    if inputs.governance_evidence:
        roles.append(("governance", inputs.governance_evidence))
    observation = tuple(ref for line in inputs.ordered_lines for ref in line.evidence)
    if observation:
        roles.append(("observation", observation))
    if inputs.coverage is not None:
        roles.append(("coverage", inputs.coverage.evidence))
    if inputs.planned_price is not None:
        roles.append(("planned_price", inputs.planned_price.evidence))
    if inputs.committed_price is not None:
        roles.append(("committed_price", inputs.committed_price.evidence))
    if inputs.required_schedule is not None:
        roles.append(("required_schedule", inputs.required_schedule.evidence))
    if inputs.commitment is not None:
        roles.append(("commitment", inputs.commitment.evidence))
    if inputs.revision is not None:
        roles.append(("supersession", inputs.revision.evidence))
    if inputs.substitution is not None:
        roles.append(("relationship", inputs.substitution.evidence))
    if inputs.resolution is not None:
        roles.append(("resolution", inputs.resolution.evidence))
    return tuple(roles)


def _qualified_input_reason(
    inputs: AnomalyAssessmentInput, scope: StateScope, as_of: datetime
) -> AssessmentReason | None:
    if scope != inputs.scope:
        return AssessmentReason.SCOPE_MISMATCH
    if as_of > inputs.as_of:
        return AssessmentReason.FUTURE_INPUT
    return None


def _roles_for(
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...], *names: str
) -> tuple[tuple[str, tuple[EvidenceRef, ...]], ...]:
    selected = set(names)
    return tuple(item for item in evidence_roles if item[0] in selected)


def _assessment_provenance(
    inputs: AnomalyAssessmentInput,
    provenance: DecisionProvenance,
    policies: QuantityAssessmentPolicies,
    kind: AnomalyKind,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
) -> DecisionProvenance:
    _, digest = _policy_contract(policies, kind)
    assessment_context_id = stable_id(
        "anomaly-assessment-context",
        inputs.subject_key,
        inputs.scope,
        inputs.as_of.isoformat(),
        tuple(sorted(inputs.governance_decision_ids)),
    )
    context = replace(
        provenance.context,
        config_digest=digest,
        input_snapshot_ids=tuple(
            sorted(
                {
                    assessment_context_id,
                    *(ref.evidence_id for ref in _flatten_evidence(evidence_roles)),
                }
            )
        ),
    )
    return replace(provenance, context=context)


def _policy_contract(policies: QuantityAssessmentPolicies, kind: AnomalyKind) -> tuple[str, str]:
    if kind is AnomalyKind.MISSING_PO:
        policy = policies.missing_purchase_order
        payload = {
            "minimum_required_quantity": str(policy.minimum_required_quantity),
            "policy_id": policy.policy_id,
        }
    elif kind is AnomalyKind.QUANTITY_MISMATCH:
        policy = policies.quantity_mismatch
        payload = {"policy_id": policy.policy_id, "tolerance": str(policy.tolerance)}
    elif kind is AnomalyKind.COVERAGE_GAP:
        policy = policies.coverage_gap
        payload = {
            "flag_non_current": policy.flag_non_current,
            "policy_id": policy.policy_id,
            "unknown_quantity_tolerance": str(policy.unknown_quantity_tolerance),
        }
    elif isinstance(policies, AnomalyAssessmentPolicies):
        if kind is AnomalyKind.SUBSTITUTION:
            policy = policies.substitution
            payload = {"policy_id": policy.policy_id, "tolerance": str(policy.tolerance)}
        elif kind is AnomalyKind.STALE_REVISION:
            payload = {"policy_id": policies.stale_revision.policy_id}
        elif kind is AnomalyKind.PRICE_DEVIATION:
            policy = policies.price_deviation
            payload = {"policy_id": policy.policy_id, "tolerance": str(policy.tolerance)}
        elif kind is AnomalyKind.LATE_COMMITMENT:
            policy = policies.late_commitment
            payload = {
                "policy_id": policy.policy_id,
                "tolerance_seconds": str(policy.tolerance.total_seconds()),
            }
        elif kind is AnomalyKind.UNRESOLVED_IDENTITY:
            payload = {"policy_id": policies.unresolved_identity.policy_id}
        else:  # pragma: no cover - exhaustive guard for future enum members
            raise SemanticContractError(f"unsupported policy kind: {kind.value}")
    else:
        raise SemanticContractError(f"policy bundle does not support kind: {kind.value}")
    configuration = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return configuration, sha256(configuration.encode()).hexdigest()


def _flatten_evidence(
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
) -> tuple[EvidenceRef, ...]:
    by_id = {ref.evidence_id: ref for _, references in evidence_roles for ref in references}
    return tuple(by_id[key] for key in sorted(by_id))


def _make_anomaly(
    inputs: AnomalyAssessmentInput,
    details: AnomalyDetails,
    severity: AnomalySeverity,
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policy_id: str,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> Anomaly:
    return Anomaly(
        inputs.subject_key,
        details,
        severity,
        AnomalyStatus.OPEN,
        _flatten_evidence(evidence_roles),
        policy_id,
        provenance,
        detected_at,
        inputs.scope,
    )


def _result(
    inputs: AnomalyAssessmentInput,
    kind: AnomalyKind,
    status: AssessmentStatus,
    reason: AssessmentReason | None,
    anomaly: Anomaly | None,
    input_ids: tuple[str, ...],
    evidence_roles: tuple[tuple[str, tuple[EvidenceRef, ...]], ...],
    policy_id: str,
    policies: QuantityAssessmentPolicies,
) -> AnomalyAssessment:
    policy_configuration, policy_digest = _policy_contract(policies, kind)
    return AnomalyAssessment(
        inputs.subject_key,
        kind,
        status,
        reason,
        anomaly,
        tuple(sorted(set(input_ids))),
        tuple(sorted(set(inputs.governance_decision_ids))),
        _input_dispositions(inputs),
        evidence_roles,
        policy_id,
        policy_configuration,
        policy_digest,
        inputs.scope,
        inputs.as_of,
    )


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise TemporalContractError(f"{name} must be timezone-aware")


def _require_evidence(name: str, evidence: tuple[EvidenceRef, ...]) -> None:
    if not evidence:
        raise SemanticContractError(f"{name} requires evidence")
    if len({ref.evidence_id for ref in evidence}) != len(evidence):
        raise SemanticContractError(f"{name} evidence must be unique")
