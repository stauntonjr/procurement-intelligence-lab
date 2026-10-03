"""Real optional graph against the application-owned review ledger."""

import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from procurement_intelligence_lab.adapters.langgraph_review import LangGraphReviewRuntime
from procurement_intelligence_lab.platform.semantics.agent_runs import RunConflict, RunNotFound
from procurement_intelligence_lab.platform.semantics.briefs import BriefConflict
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.workflows import WorkflowError, WorkflowRequest
from tests.contract.test_exact_brief_review import ARGS, HUMAN, NOW, setup

REQUEST = WorkflowRequest(ARGS.request.canonical_key, ARGS.request.as_of)


def runtime(path: Path) -> LangGraphReviewRuntime:
    service, _ = setup(path)
    return LangGraphReviewRuntime(service, path)


def test_durable_pause_review_repeated_resume_and_source_success(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    graph = runtime(path)
    view = graph.start(REQUEST, context=HUMAN)
    assert view.status == "awaiting_review" and view.brief is not None and view.saved is None
    assert '"ordered_quantity":"6"' in view.brief.content_json
    events = graph.service.tools.runs.events(view.run_id, context=HUMAN)
    assert sum(e.kind.value == "tool_succeeded" for e in events) == 2
    # A new adapter/checkpointer instance, no retained invocation context.
    graph = runtime(path)
    assert graph.status(view.run_id, context=HUMAN) == view
    done = graph.review(
        view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN
    )
    assert done.status == "completed" and done.saved is not None
    assert (
        graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)
        == done
    )
    assert graph.status(view.run_id, context=HUMAN) == done
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1


def test_owner_and_version_checked_before_checkpoint_load(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    with pytest.raises(RunNotFound):
        graph.status(view.run_id, context=replace(HUMAN, project_id="delta"))
    with pytest.raises(ScopeAuthorizationError):
        graph.status(
            view.run_id, context=replace(HUMAN, permissions=frozenset({Permission.READ_STATE}))
        )
    graph.service.tools.runs.versions = replace(graph.service.tools.runs.versions, prompt="changed")
    with pytest.raises(RunConflict):
        graph.status(view.run_id, context=HUMAN)


def test_rejection_digest_and_operational_authority(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    assert view.brief is not None
    with pytest.raises(BriefConflict):
        graph.review(view.run_id, view.brief.brief_id, "0" * 64, "approve", context=HUMAN)
    operational = replace(
        HUMAN, permissions=frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE})
    )
    with pytest.raises(ScopeAuthorizationError):
        graph.review(
            view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=operational
        )
    rejected = graph.review(
        view.run_id, view.brief.brief_id, view.brief.digest, "reject", context=HUMAN
    )
    assert rejected.status == "rejected" and rejected.saved is None
    with pytest.raises(BriefConflict):
        graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)


def test_expired_receipt_and_changed_facts_fail_closed(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    assert view.brief is not None
    graph.service.review(
        view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN
    )
    graph.service.clock = lambda: NOW + timedelta(hours=1)
    with pytest.raises(BriefConflict):
        graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)
    graph.service.clock = lambda: NOW
    result = graph.service.tools.investigator.investigate(ARGS.request, context=HUMAN)
    changed = Mock()
    changed.investigate.return_value = replace(result, snapshot_id="changed")
    graph.service.tools = replace(graph.service.tools, investigator=changed)
    with pytest.raises(BriefConflict):
        graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)


def test_missing_checkpoint_is_unknown_not_completed(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    run = graph.service.tools.runs.start(context=HUMAN)
    with pytest.raises(WorkflowError):
        graph.status(run.run_id, context=HUMAN)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_step_budget(tmp_path: Path, limit: int) -> None:
    graph = runtime(tmp_path / "runs.db")
    with pytest.raises(ValueError):
        LangGraphReviewRuntime(graph.service, graph.database, max_steps=limit)


def test_checkpoint_contains_no_permission_or_context(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    with sqlite3.connect(graph.checkpoint_path) as db:
        raw = repr(db.execute("SELECT checkpoint FROM checkpoints").fetchall())
    for private in ("permissions", "human-brief-cli", "principal_id", "approved", "api_key"):
        assert private not in raw
    assert view.brief is not None


def test_terminal_rejection_requires_durable_receipt(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    assert view.brief is not None
    graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "reject", context=HUMAN)
    with sqlite3.connect(graph.database) as db:
        db.execute("DELETE FROM brief_receipts")
    with pytest.raises(WorkflowError):
        graph.status(view.run_id, context=HUMAN)


def test_orphan_draft_can_recover_without_redrafting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = runtime(tmp_path / "runs.db")
    original = graph.service.draft
    observed: list[str] = []

    from procurement_intelligence_lab.application.corpus_agent_tools import InvestigateToolArgs
    from procurement_intelligence_lab.platform.semantics.briefs import ReviewBrief
    from procurement_intelligence_lab.platform.semantics.scope import RequestContext

    def crash(run_id: str, args: InvestigateToolArgs, *, context: RequestContext) -> ReviewBrief:
        brief = original(run_id, args, context=context)
        observed.append(brief.run.run_id)
        raise RuntimeError("crash after durable draft")

    monkeypatch.setattr(graph.service, "draft", crash)
    with pytest.raises(RuntimeError, match="crash"):
        graph.start(REQUEST, context=HUMAN)
    monkeypatch.setattr(graph.service, "draft", original)
    recovered = graph.recover(observed[0], context=HUMAN)
    assert recovered.status == "awaiting_review"
    assert recovered.brief.version == 1
    with sqlite3.connect(graph.database) as db:
        assert db.execute("SELECT COUNT(*) FROM review_briefs").fetchone()[0] == 1


def test_concurrent_resumes_return_one_result(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "runs.db"
    view = runtime(path).start(REQUEST, context=HUMAN)

    def approve(_: int):
        return runtime(path).review(
            view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(approve, range(3)))
    assert results[0] == results[1] == results[2]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1


def test_deadline_and_one_failed_read_without_success(tmp_path: Path) -> None:
    from procurement_intelligence_lab.application.corpus_agent_tools import ToolExecutionError
    from procurement_intelligence_lab.platform.semantics.workflows import WorkflowBudgetExceeded

    graph = runtime(tmp_path / "runs.db")
    tiny = LangGraphReviewRuntime(graph.service, graph.database, timeout_seconds=1e-9)
    with pytest.raises(WorkflowBudgetExceeded):
        tiny.start(REQUEST, context=HUMAN)
    investigator = Mock()
    investigator.investigate.side_effect = TimeoutError("private timeout details")
    graph.service.tools = replace(graph.service.tools, investigator=investigator)
    with pytest.raises(ToolExecutionError):
        graph.start(REQUEST, context=HUMAN)
    assert investigator.investigate.call_count == 1
    with sqlite3.connect(graph.database) as db:
        assert db.execute("SELECT COUNT(*) FROM review_briefs").fetchone()[0] == 0


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf"), 121])
def test_invalid_deadline(tmp_path: Path, value: float) -> None:
    graph = runtime(tmp_path / "runs.db")
    with pytest.raises(ValueError):
        LangGraphReviewRuntime(graph.service, graph.database, timeout_seconds=value)


def test_checkpoint_digest_tampering_and_active_replacement(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    config = graph._config(view.run_id, HUMAN)  # pyright: ignore[reportPrivateUsage]
    with graph._graph() as compiled:  # pyright: ignore[reportPrivateUsage]
        compiled.update_state(config, {"digest": "0" * 64})
    with pytest.raises(WorkflowError):
        graph.status(view.run_id, context=HUMAN)
    with graph._graph() as compiled:  # pyright: ignore[reportPrivateUsage]
        compiled.update_state(config, {"digest": view.brief.digest})
    graph.service.draft(view.run_id, ARGS, context=HUMAN)
    with pytest.raises(BriefConflict):
        graph.status(view.run_id, context=HUMAN)


def test_unauthorized_call_does_not_open_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    opened = Mock(side_effect=AssertionError("checkpoint must not load"))
    monkeypatch.setattr(graph, "_graph", opened)
    with pytest.raises(RunNotFound):
        graph.status(view.run_id, context=replace(HUMAN, principal_id="other-human"))
    opened.assert_not_called()


def test_environment_tracing_is_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from langsmith.run_helpers import get_tracing_context

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    graph = runtime(tmp_path / "runs.db")
    with graph._graph():  # pyright: ignore[reportPrivateUsage]
        assert get_tracing_context()["enabled"] is False


@pytest.mark.parametrize("item", ["", "  ", "x" * 101])
def test_request_contract_rejects_empty_and_oversized(item: str) -> None:
    from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError

    with pytest.raises(SemanticContractError):
        WorkflowRequest(item, NOW)
    with pytest.raises(SemanticContractError):
        WorkflowRequest("GPU-A", NOW.replace(tzinfo=None))


@pytest.mark.parametrize(
    "table,mutation",
    [
        ("brief_receipts", "DELETE FROM brief_receipts"),
        ("saved_briefs", "UPDATE saved_briefs SET idempotency_key='foreign'"),
        ("saved_briefs", "UPDATE saved_briefs SET payload='{}'"),
        ("brief_receipts", "UPDATE brief_receipts SET payload='{}'"),
    ],
)
def test_authoritative_status_rejects_corrupt_result_or_receipt(
    tmp_path: Path, table: str, mutation: str
) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)
    with sqlite3.connect(graph.database) as db:
        db.execute(mutation)
    from procurement_intelligence_lab.platform.semantics.briefs import BriefIntegrityError

    with pytest.raises(BriefIntegrityError):
        graph.status(view.run_id, context=HUMAN)


def test_completed_approval_acknowledgment_revalidates_current_evidence(tmp_path: Path) -> None:
    graph = runtime(tmp_path / "runs.db")
    view = graph.start(REQUEST, context=HUMAN)
    graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)
    original = graph.service.tools.investigator.investigate(ARGS.request, context=HUMAN)
    changed = Mock()
    changed.investigate.return_value = replace(original, snapshot_id="changed-after-completion")
    graph.service.tools = replace(graph.service.tools, investigator=changed)
    assert graph.status(view.run_id, context=HUMAN).status == "completed"
    with pytest.raises(BriefConflict):
        graph.review(view.run_id, view.brief.brief_id, view.brief.digest, "approve", context=HUMAN)
    assert changed.investigate.call_count == 1
    with sqlite3.connect(graph.database) as db:
        assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1
