"""Universal approval-gated and idempotent action-result contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.decisions import (
    Decision,
    DecisionAuthority,
    DecisionOutcome,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    AuthorityContractError,
    AuthorityScopeMismatchError,
    IdempotencyContractError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance


@dataclass(frozen=True)
class ActionApproval:
    decision_id: str
    authority: DecisionAuthority
    approved_at: datetime
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise AuthorityContractError("approval decision ID is required")
        if not self.authority.may_approve_actions:
            raise AuthorityContractError("approval authority must explicitly permit actions")
        if self.approved_at.tzinfo is None:
            raise TemporalContractError("approval timestamp must be timezone-aware")
        if not self.evidence:
            raise AuthorityContractError("action approval requires evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise AuthorityContractError("action approval evidence must be unique")

    @property
    def approval_id(self) -> str:
        return stable_id(
            "action-approval",
            self.decision_id,
            self.authority.authority_id,
            self.approved_at.isoformat(),
            tuple(item.evidence_id for item in self.evidence),
        )


@dataclass(frozen=True)
class ApprovedDecision:
    decision: Decision
    approval: ActionApproval

    def __post_init__(self) -> None:
        if self.decision.outcome is not DecisionOutcome.RECOMMEND:
            raise AuthorityContractError("only recommended decisions may be approved")
        if self.approval.decision_id != self.decision.decision_id:
            raise AuthorityContractError("approval must reference the exact decision")
        if self.approval.authority.scope != self.decision.inputs.scope:
            raise AuthorityScopeMismatchError("approval and decision must share one scope")
        if self.approval.approved_at < self.decision.decided_at:
            raise TemporalContractError("approval cannot precede the decision")


class ActionStatus(StrEnum):
    ATTEMPTED = "attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ActionResult:
    approved_decision: ApprovedDecision
    action_kind: str
    idempotency_key: str
    status: ActionStatus
    attempted_at: datetime
    evidence: tuple[EvidenceRef, ...]
    provenance: DecisionProvenance
    completed_at: datetime | None = None
    external_reference: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.action_kind.strip():
            raise SemanticContractError("action kind is required")
        if not self.idempotency_key.strip():
            raise IdempotencyContractError("action idempotency key is required")
        if self.attempted_at.tzinfo is None:
            raise TemporalContractError("action attempted_at must be timezone-aware")
        if self.attempted_at < self.approved_decision.approval.approved_at:
            raise TemporalContractError("action attempt cannot precede approval")
        if self.completed_at is not None:
            if self.completed_at.tzinfo is None:
                raise TemporalContractError("action completed_at must be timezone-aware")
            if self.completed_at < self.attempted_at:
                raise TemporalContractError("action completion cannot precede its attempt")
        if not self.evidence:
            raise SemanticContractError("action results require audit evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("action-result evidence must be unique")
        if self.external_reference is not None and not self.external_reference.strip():
            raise SemanticContractError("external_reference must be non-empty when present")
        if self.status is ActionStatus.ATTEMPTED:
            if self.completed_at is not None or self.failure_reason is not None:
                raise SemanticContractError(
                    "attempted actions cannot carry completion or failure details"
                )
        elif self.completed_at is None:
            raise SemanticContractError("completed action statuses require completed_at")
        if self.status is ActionStatus.FAILED and not self.failure_reason:
            raise SemanticContractError("failed actions require a failure reason")
        if self.status is not ActionStatus.FAILED and self.failure_reason is not None:
            raise SemanticContractError("only failed actions may carry a failure reason")

    @property
    def action_id(self) -> str:
        return stable_id(
            "action-result",
            self.approved_decision.decision.decision_id,
            self.approved_decision.approval.approval_id,
            self.action_kind,
            self.idempotency_key,
            self.status.value,
            self.attempted_at.isoformat(),
            self.completed_at.isoformat() if self.completed_at is not None else None,
            self.external_reference,
            self.failure_reason,
            tuple(item.evidence_id for item in self.evidence),
            self.provenance.provenance_id,
        )
