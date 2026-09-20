"""Qualified, evidence-backed procurement anomaly assessment."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from procurement_intelligence_lab.domains.procurement.anomalies import (
    AnomalyKind,
    CoverageGapDetails,
    CoverageGapPolicy,
    MissingPurchaseOrderDetails,
    MissingPurchaseOrderPolicy,
    QuantityMismatchPolicy,
    detect_quantity_mismatch,
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

    def __post_init__(self) -> None:
        if not self.subject_key.strip() or not self.expected_unit.strip():
            raise SemanticContractError("assessment subject and expected unit are required")
        _require_aware("assessment as_of", self.as_of)
        if any(not item.strip() for item in self.governance_decision_ids):
            raise SemanticContractError("governance decision IDs must not be blank")
        if self.expected is not None:
            if self.expected.canonical_key != self.subject_key:
                raise SemanticContractError("expected requirement subject must match assessment")
            if self.expected.scope != self.scope:
                raise ScopeContractError("expected requirement scope must match assessment")
            if self.expected.as_of > self.as_of:
                raise TemporalContractError("expected requirement cannot be future-dated")


@dataclass(frozen=True)
class AnomalyAssessment:
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
    evidence_roles = _evidence_roles(inputs)
    invalid_reason, lines = _admit_lines(inputs)
    missing = _assess_missing_po(
        inputs, lines, invalid_reason, evidence_roles, policy, provenance, detected_at
    )
    quantity = _assess_quantity_mismatch(
        inputs, lines, invalid_reason, evidence_roles, policy, provenance, detected_at
    )
    coverage = _assess_coverage(inputs, evidence_roles, policy, provenance, detected_at)
    return missing, quantity, coverage


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
    if coverage.subject_key != inputs.subject_key or coverage.scope != inputs.scope:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.SCOPE_MISMATCH,
            None,
            (coverage.attestation_id,),
            evidence_roles,
            policy.coverage_gap.policy_id,
            policy,
        )
    if coverage.as_of > inputs.as_of:
        return _result(
            inputs,
            kind,
            AssessmentStatus.NOT_ASSESSED,
            AssessmentReason.FUTURE_INPUT,
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
    values = set(dispositions.values())
    if "rejected_scope" in values:
        return AssessmentReason.SCOPE_MISMATCH, ()
    if "rejected_future" in values:
        return AssessmentReason.FUTURE_INPUT, ()
    if "rejected_ineligible" in values:
        return AssessmentReason.INELIGIBLE_INPUT, ()
    if "conflicting_version" in values:
        return AssessmentReason.CONFLICTING_INPUT, ()
    eligible = {
        line.assertion_id: line
        for line in inputs.ordered_lines
        if dispositions[line.line_id] == "eligible"
    }
    return None, tuple(sorted(eligible.values(), key=lambda item: item.line_id))


def _input_dispositions(inputs: AnomalyAssessmentInput) -> tuple[tuple[str, str], ...]:
    dispositions: dict[str, str] = {}
    by_assertion: dict[str, QualifiedOrderLine] = {}
    ordered = sorted(
        inputs.ordered_lines,
        key=lambda item: (item.assertion_id, item.line_id, item.evidence[0].evidence_id),
    )
    for line in ordered:
        if line.scope != inputs.scope:
            dispositions[line.line_id] = "rejected_scope"
            continue
        if line.as_of > inputs.as_of:
            dispositions[line.line_id] = "rejected_future"
            continue
        if not line.approved:
            dispositions[line.line_id] = "rejected_ineligible"
            continue
        prior = by_assertion.get(line.assertion_id)
        if prior is None:
            by_assertion[line.assertion_id] = line
            dispositions[line.line_id] = "eligible"
        elif prior.replay_identity == line.replay_identity:
            if prior.line_id != line.line_id:
                dispositions[line.line_id] = "exact_replay"
        else:
            dispositions[prior.line_id] = "conflicting_version"
            dispositions[line.line_id] = "conflicting_version"
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
    return tuple(roles)


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
    return AnomalyAssessment(
        kind,
        status,
        reason,
        anomaly,
        tuple(sorted(set(input_ids))),
        tuple(sorted(set(inputs.governance_decision_ids))),
        _input_dispositions(inputs),
        evidence_roles,
        policy_id,
        policies.canonical_configuration,
        policies.digest,
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
