from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.sqlite_reconciliation_reviews import (
    ReconciliationReviewStoreError,
    SqliteReconciliationReviewStore,
)
from procurement_intelligence_lab.domains.procurement.review_reconciliation import (
    HumanReconciliationDecision,
    ReconciliationReviewOutcome,
    prospective_decision_id,
)
from procurement_intelligence_lab.platform.semantics.briefs import BriefConflict
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)
CONTEXT = RequestContext(
    "reviewer",
    "tenant",
    "project",
    "site",
    frozenset({Permission.REVIEW, Permission.READ_STATE, Permission.READ_EVIDENCE}),
    "trace",
)


def make_decision(**changes: object) -> HumanReconciliationDecision:
    values: dict[str, object] = {
        "brief_id": "brief-1",
        "brief_digest": "b" * 64,
        "subject_key": "GPU-A",
        "scope": StateScope("tenant", "project", "site", "snapshot"),
        "outcome": ReconciliationReviewOutcome.SELECT_GOVERNING_REVISION,
        "candidate_claim_ids": ("claim-a", "claim-b"),
        "selected_claim_id": "claim-a",
        "rationale": "Revision A governs prospectively.",
        "reviewer_id": "reviewer",
        "policy_id": "human-required-quantity/v1",
        "recorded_at": NOW,
        "effective_at": NOW,
        "evidence": (EvidenceRef("bom-a", "a" * 64, RecordLocation("bom", "A")),),
    }
    values.update(changes)
    return HumanReconciliationDecision(decision_id=prospective_decision_id(**values), **values)  # type: ignore[arg-type]


def test_store_is_prospective_scoped_and_idempotent(tmp_path: Path) -> None:
    store = SqliteReconciliationReviewStore(tmp_path / "review.sqlite")
    item = make_decision()
    assert store.record(item, context=CONTEXT) == item
    assert store.record(item, context=CONTEXT) == item
    assert store.latest("GPU-A", NOW - timedelta(microseconds=1), context=CONTEXT) is None
    assert store.latest("GPU-A", NOW, context=CONTEXT) == item
    assert store.latest("GPU-B", NOW, context=CONTEXT) is None
    assert store.for_brief("brief-1", context=CONTEXT) == item


def test_store_rejects_changed_replay_and_scope(tmp_path: Path) -> None:
    store = SqliteReconciliationReviewStore(tmp_path / "review.sqlite")
    store.record(make_decision(), context=CONTEXT)
    with pytest.raises(BriefConflict, match="replay"):
        store.record(make_decision(rationale="Different rationale."), context=CONTEXT)
    foreign = replace(CONTEXT, site_id="other")
    with pytest.raises(BriefConflict, match="scope"):
        store.record(make_decision(), context=foreign)


def test_corrupt_payload_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "review.sqlite"
    store = SqliteReconciliationReviewStore(path)
    store.record(make_decision(), context=CONTEXT)
    import sqlite3

    with sqlite3.connect(path) as db:
        db.execute("UPDATE reconciliation_reviews SET payload='{}'")
    with pytest.raises(ReconciliationReviewStoreError, match="invalid stored"):
        store.latest("GPU-A", NOW, context=CONTEXT)
