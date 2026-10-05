"""Human reconciliation decisions for one exact procurement state scope."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class ReconciliationReviewOutcome(StrEnum):
    SELECT_GOVERNING_REVISION = "select_governing_revision"
    KEEP_UNRESOLVED = "keep_unresolved"
    CONFIRM_ASSESSMENT = "confirm_assessment"
    ASSESSMENT_NEEDS_CORRECTION = "assessment_needs_correction"


def prospective_decision_id(
    *,
    brief_id: str,
    brief_digest: str,
    subject_key: str,
    scope: StateScope,
    outcome: ReconciliationReviewOutcome,
    candidate_claim_ids: tuple[str, ...],
    selected_claim_id: str | None,
    rationale: str,
    reviewer_id: str,
    policy_id: str,
    recorded_at: datetime,
    effective_at: datetime,
    evidence: tuple[EvidenceRef, ...],
) -> str:
    return stable_id(
        "human-reconciliation-decision",
        brief_id,
        brief_digest,
        subject_key,
        scope,
        outcome.value,
        candidate_claim_ids,
        selected_claim_id,
        rationale,
        reviewer_id,
        policy_id,
        recorded_at.isoformat(),
        effective_at.isoformat(),
        tuple(item.evidence_id for item in evidence),
    )


@dataclass(frozen=True)
class HumanReconciliationDecision:
    decision_id: str
    brief_id: str
    brief_digest: str
    subject_key: str
    scope: StateScope
    outcome: ReconciliationReviewOutcome
    candidate_claim_ids: tuple[str, ...]
    selected_claim_id: str | None
    rationale: str
    reviewer_id: str
    policy_id: str
    recorded_at: datetime
    effective_at: datetime
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        texts = (
            self.brief_id,
            self.brief_digest,
            self.subject_key,
            self.reviewer_id,
            self.policy_id,
        )
        if any(type(value) is not str or not value.strip() or len(value) > 500 for value in texts):
            raise SemanticContractError("reconciliation identifiers require bounded text")
        if len(self.brief_digest) != 64 or any(
            c not in "0123456789abcdef" for c in self.brief_digest
        ):
            raise SemanticContractError("reconciliation requires a SHA256 brief digest")
        if not self.candidate_claim_ids:
            raise SemanticContractError("reconciliation requires candidate claims")
        if len(set(self.candidate_claim_ids)) != len(self.candidate_claim_ids):
            raise SemanticContractError("candidate claims must be unique")
        if not self.evidence:
            raise SemanticContractError("reconciliation requires evidence")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise SemanticContractError("reconciliation evidence must be unique")
        for value in (self.recorded_at, self.effective_at):
            if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
                raise SemanticContractError("reconciliation times must be timezone-aware")
        if self.effective_at != self.recorded_at:
            raise SemanticContractError("effective time must equal recorded time")
        selecting = self.outcome is ReconciliationReviewOutcome.SELECT_GOVERNING_REVISION
        if selecting and self.selected_claim_id is None:
            raise SemanticContractError("governing selection requires one selected candidate")
        if selecting and self.selected_claim_id not in self.candidate_claim_ids:
            raise SemanticContractError("selected claim must be a candidate")
        if not selecting and self.selected_claim_id is not None:
            raise SemanticContractError("non-selection outcome cannot select a claim")
        if self.outcome in (
            ReconciliationReviewOutcome.SELECT_GOVERNING_REVISION,
            ReconciliationReviewOutcome.KEEP_UNRESOLVED,
        ) and (not self.rationale.strip() or len(self.rationale) > 2000):
            raise SemanticContractError("reconciliation decision requires a rationale")
        expected = prospective_decision_id(
            brief_id=self.brief_id,
            brief_digest=self.brief_digest,
            subject_key=self.subject_key,
            scope=self.scope,
            outcome=self.outcome,
            candidate_claim_ids=self.candidate_claim_ids,
            selected_claim_id=self.selected_claim_id,
            rationale=self.rationale,
            reviewer_id=self.reviewer_id,
            policy_id=self.policy_id,
            recorded_at=self.recorded_at,
            effective_at=self.effective_at,
            evidence=self.evidence,
        )
        if self.decision_id != expected:
            raise SemanticContractError("reconciliation decision identity is invalid")
