from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
    ReviewedSourceSkuQuery,
    reviewed_dependency_manifest,
    reviewed_query_provenance,
)
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewDecision,
    DocumentReviewTask,
    ReviewDecisionCommand,
    ReviewHistory,
    ReviewOutcome,
    ReviewProposal,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import SourceQueryContractError
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.contract.test_postgres_archive import inputs
from tests.unit.test_source_sku_query import execution


def review(
    snapshot: DocumentSnapshot, value: str | None = "GPU-B", index: int = 0, request: str = "review"
) -> ReviewHistory:
    previous = [a for a in snapshot.assertions if a.predicate.value == "has_sku"][index]
    task = DocumentReviewTask(
        ReviewProposal(
            snapshot.artifact.source.scope,
            request,
            snapshot.snapshot_id,
            previous,
            value,
            "checked source",
            "human",
        ),
        AT + timedelta(seconds=2),
    )
    command = ReviewDecisionCommand(
        task.proposal.scope,
        "decision-" + request,
        task.task_id,
        task.digest,
        ReviewOutcome.APPROVE,
        "reviewer",
        "approved",
    )
    return ReviewHistory(task, DocumentReviewDecision(command, AT + timedelta(seconds=3)))


def run(
    snapshot: DocumentSnapshot,
    reviews: Iterable[ReviewHistory],
    *,
    as_of: datetime = AT + timedelta(seconds=4),
    context: ProvenanceContext | None = None,
) -> ReviewedSourceSkuQuery:
    ctx = context or replace(
        execution(snapshot.snapshot_id),
        workflow_name="reviewed-source-sku-query",
        started_at=AT + timedelta(seconds=5),
    )
    return ReviewedSourceSkuQuery(snapshot, tuple(reviews), as_of, reviewed_query_provenance(ctx))


def test_corrects_one_duplicate_token_and_retains_real_input_edges(tmp_path: Path):
    snapshot, _ = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8"))
    r = review(snapshot)
    assert r.correction_id is not None
    result = run(snapshot, [r])
    assert result.value == ("GPU-A", "GPU-B") and result.status is EpistemicStatus.INFERRED
    assert [a.value for a in snapshot.assertions if a.predicate.value == "has_sku"] == [
        "GPU-A",
        "GPU-A",
    ]
    row = result.rows[0]
    assert row.value == "GPU-B"
    assert {e.target_id for e in row.event.input_edges} == {
        r.task.proposal.previous.assertion_id,
        r.correction_id,
    }
    graph = reviewed_dependency_manifest(result, "request")
    assert len(graph.roots) == 3 and len(graph.claims) == 2
    assert graph.impact(r.correction_id, 2).affected == tuple(
        sorted(((row.reference_id, 1), (result.reference_id, 2)))
    )
    assert {e.target_id for e in result.event.input_edges} == {
        row.reference_id,
        result.inputs[1][0],
    }


@pytest.mark.parametrize("proposed", [None, "GPU-A", "gpu-a", "0", "-1", "0.5"])
def test_null_equal_case_and_numeric_looking_strings(tmp_path: Path, proposed: str | None):
    snapshot, _ = inputs(tmp_path)
    result = run(snapshot, [review(snapshot, proposed)])
    assert result.value is None if proposed is None else result.value == (proposed,)
    assert result.status is (
        EpistemicStatus.UNRESOLVED if proposed is None else EpistemicStatus.INFERRED
    )
    assert bool(result.missing_reference_ids) == (proposed is None)


def test_resolves_selected_unknown_but_preserves_unselected_unknown(tmp_path: Path):
    missing = ROW.replace('<c r="A7"><v>GPU-A</v></c>', "")
    snapshot, _ = inputs(
        tmp_path, HEADER + missing + ROW.replace("7", "8").replace('<c r="A8"><v>GPU-A</v></c>', "")
    )
    result = run(snapshot, [review(snapshot)])
    assert result.value is None and result.known_skus == ("GPU-B",)
    assert len(result.missing_reference_ids) == 1


def test_selection_order_invariance_and_asof_identity(tmp_path: Path):
    snapshot, _ = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8"))
    a, b = review(snapshot, index=0, request="a"), review(snapshot, index=1, request="b")
    first = run(snapshot, [a, b])
    again = run(snapshot, [b, a])
    later = run(snapshot, [a, b], as_of=AT + timedelta(seconds=5))
    assert first.reference_id == again.reference_id
    assert reviewed_dependency_manifest(first, "request") == reviewed_dependency_manifest(
        again, "request"
    )
    assert first.value == later.value and first.reference_id != later.reference_id


@pytest.mark.parametrize(
    "kind",
    ["empty", "duplicate", "conflict", "pending", "rejected", "non_sku", "future", "foreign"],
)
def test_invalid_review_selection_is_intrinsically_rejected(tmp_path: Path, kind: str):
    snapshot, _ = inputs(tmp_path)
    a = review(snapshot)
    assert a.decision is not None
    selected = [a]
    asof = AT + timedelta(seconds=4)
    if kind == "empty":
        selected = []
    if kind == "duplicate":
        selected = [a, a]
    if kind == "conflict":
        selected = [a, review(snapshot, request="another")]
    if kind == "pending":
        selected = [replace(a, decision=None)]
    if kind == "rejected":
        selected = [
            replace(
                a,
                decision=replace(
                    a.decision, command=replace(a.decision.command, outcome=ReviewOutcome.REJECT)
                ),
            )
        ]
    if kind == "non_sku":
        previous = next(x for x in snapshot.assertions if x.predicate.value == "has_description")
        task = replace(a.task, proposal=replace(a.task.proposal, previous=previous))
        selected = [
            ReviewHistory(
                task,
                replace(a.decision, command=replace(a.decision.command, task_digest=task.digest)),
            )
        ]
    if kind == "future":
        asof = AT + timedelta(seconds=2)
    if kind == "foreign":
        task = replace(a.task, proposal=replace(a.task.proposal, snapshot_id="foreign"))
        selected = [
            ReviewHistory(
                task,
                replace(a.decision, command=replace(a.decision.command, task_digest=task.digest)),
            )
        ]
    with pytest.raises(SourceQueryContractError):
        run(snapshot, selected, as_of=asof)


@pytest.mark.parametrize("count", [32, 33])
def test_full_review_budget_uses_intermediate_producers(tmp_path: Path, count: int):
    snapshot, _ = inputs(
        tmp_path, HEADER + "".join(ROW.replace("7", str(i)) for i in range(2, count + 2))
    )
    selected = [review(snapshot, index=i, request=str(i)) for i in range(count)]
    if count == 33:
        with pytest.raises(SourceQueryContractError):
            run(snapshot, selected)
    else:
        result = run(snapshot, selected)
        graph = reviewed_dependency_manifest(result, "request")
        assert len(graph.roots) == 64 and len(graph.claims) == 33
        assert max(len(c.inputs) for c in graph.claims) == 32
        assert result.value == ("GPU-B",)


class Foreign(StrEnum):
    DETERMINISTIC = "deterministic"


@pytest.mark.parametrize(
    "changes",
    [
        {"component_kind": "deterministic"},
        {"component_kind": Foreign.DETERMINISTIC},
        {"policy_version": "other"},
    ],
)
def test_fixed_provenance_is_intrinsic(tmp_path: Path, changes: dict[str, Any]):
    snapshot, _ = inputs(tmp_path)
    r = review(snapshot)
    ctx = replace(
        execution(snapshot.snapshot_id),
        workflow_name="reviewed-source-sku-query",
        started_at=AT + timedelta(seconds=5),
    )
    with pytest.raises(SourceQueryContractError):
        ReviewedSourceSkuQuery(
            snapshot,
            (r,),
            AT + timedelta(seconds=4),
            replace(reviewed_query_provenance(ctx), **changes),
        )


def test_reference_binds_full_review_content_and_timestamp_encoding(tmp_path: Path):
    from datetime import timezone

    snapshot, _ = inputs(tmp_path)
    original = review(snapshot)
    assert original.decision is not None
    changed = replace(
        original,
        decision=replace(
            original.decision,
            command=replace(original.decision.command, reason="another retained rationale"),
        ),
    )
    encoded = replace(
        original,
        decision=replace(
            original.decision,
            recorded_at=original.decision.recorded_at.astimezone(timezone(timedelta(hours=2))),
        ),
    )
    first = run(snapshot, [original])
    assert first.reference_id != run(snapshot, [changed]).reference_id
    assert first.reference_id != run(snapshot, [encoded]).reference_id


def test_selected_missing_sku_can_be_resolved_completely(tmp_path: Path):
    missing = ROW.replace('<c r="A7"><v>GPU-A</v></c>', "")
    snapshot, _ = inputs(tmp_path, HEADER + missing)
    result = run(snapshot, [review(snapshot)])
    assert result.value == ("GPU-B",) and result.missing_reference_ids == ()


def test_empty_source_and_malformed_selection_time_fail_typed(tmp_path: Path):
    snapshot, _ = inputs(tmp_path)
    r = review(snapshot)
    empty, _ = inputs(tmp_path, HEADER)
    with pytest.raises(SourceQueryContractError):
        run(empty, [r])
    with pytest.raises(SourceQueryContractError):
        run(snapshot, [r], as_of=AT.replace(tzinfo=None))
    with pytest.raises(SourceQueryContractError):
        run(snapshot, [r], as_of=AT + timedelta(seconds=6))
