from datetime import UTC, datetime

import pytest

from procurement_intelligence_lab.domains.procurement.review_reconciliation import (
    HumanReconciliationDecision,
    ReconciliationReviewOutcome,
    prospective_decision_id,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope


NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)
SCOPE = StateScope("tenant", "project", "site", "v1")
EVIDENCE = (EvidenceRef("bom-a", "a" * 64, RecordLocation("bom", "A")),)


def decision(**changes: object) -> HumanReconciliationDecision:
    values: dict[str, object] = {
        "decision_id": "",
        "brief_id": "brief-1",
        "brief_digest": "b" * 64,
        "subject_key": "GPU-A",
        "scope": SCOPE,
        "outcome": ReconciliationReviewOutcome.SELECT_GOVERNING_REVISION,
        "candidate_claim_ids": ("claim-a", "claim-b"),
        "selected_claim_id": "claim-a",
        "rationale": "Revision A remains the approved requirement for this scope.",
        "reviewer_id": "reviewer-1",
        "policy_id": "human-required-quantity/v1",
        "recorded_at": NOW,
        "effective_at": NOW,
        "evidence": EVIDENCE,
    }
    values.update(changes)
    values["decision_id"] = prospective_decision_id(**{k: v for k, v in values.items() if k != "decision_id"})
    return HumanReconciliationDecision(**values)  # type: ignore[arg-type]


def test_all_review_outcomes_construct_with_compatible_fields() -> None:
    assert decision().selected_claim_id == "claim-a"
    assert decision(
        outcome=ReconciliationReviewOutcome.KEEP_UNRESOLVED,
        selected_claim_id=None,
        rationale="Neither revision has enough authority yet.",
    ).outcome is ReconciliationReviewOutcome.KEEP_UNRESOLVED
    for outcome in (
        ReconciliationReviewOutcome.CONFIRM_ASSESSMENT,
        ReconciliationReviewOutcome.ASSESSMENT_NEEDS_CORRECTION,
    ):
        assert decision(outcome=outcome, selected_claim_id=None, rationale="").outcome is outcome


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"selected_claim_id": None}, "requires one selected candidate"),
        ({"selected_claim_id": "claim-x"}, "selected claim must be a candidate"),
        ({"rationale": ""}, "requires a rationale"),
        ({"candidate_claim_ids": ("claim-a", "claim-a")}, "candidate claims must be unique"),
        ({"evidence": ()}, "requires evidence"),
        ({"evidence": EVIDENCE + EVIDENCE}, "evidence must be unique"),
        ({"effective_at": NOW.replace(hour=13)}, "effective time must equal recorded time"),
    ],
)
def test_invalid_selection_contract_fails(changes: dict[str, object], message: str) -> None:
    with pytest.raises(SemanticContractError, match=message):
        decision(**changes)


def test_nonselection_outcome_rejects_selected_claim() -> None:
    with pytest.raises(SemanticContractError, match="cannot select a claim"):
        decision(outcome=ReconciliationReviewOutcome.CONFIRM_ASSESSMENT)


def test_identity_changes_with_exact_scope() -> None:
    other = decision(scope=StateScope("tenant", "project", "other-site", "v1"))
    assert other.decision_id != decision().decision_id


def test_naive_times_and_incorrect_identity_fail() -> None:
    with pytest.raises(SemanticContractError, match="timezone-aware"):
        decision(recorded_at=NOW.replace(tzinfo=None), effective_at=NOW.replace(tzinfo=None))
    with pytest.raises(SemanticContractError, match="identity"):
        HumanReconciliationDecision(**{**decision().__dict__, "decision_id": "wrong"})
