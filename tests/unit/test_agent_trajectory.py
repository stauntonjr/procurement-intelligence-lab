"""Positive evidence is required; mock/replay never inflate live counts."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from procurement_intelligence_lab.adapters.sqlite_agent_runs import SqliteRunStore
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.agent_trajectory import (
    evaluate_trajectory,
    summarize_trajectories,
)
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEventKind,
    ExecutionKind,
    RunVersions,
    event_dto,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


def test_required_tool_success_terminal_and_replay(tmp_path: Path) -> None:
    context = RequestContext(
        "demo", "synthetic-tenant", "atlas", "lab", frozenset({Permission.READ_STATE}), "test"
    )
    app = AgentRunService(
        SqliteRunStore(tmp_path / "runs.db"),
        versions=RunVersions("fixture", "none", "p1", "t1", "f1", "a1"),
        execution_kind=ExecutionKind.FIXTURE,
        clock=lambda: datetime(2026, 10, 3, tzinfo=UTC),
    )
    run = app.start(context=context)
    root = app.events(run.run_id, context=context)[0]
    assert evaluate_trajectory(run, (), required_tools=("investigate",)).outcome == "unknown"
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=context,
    )
    assert (
        evaluate_trajectory(
            run, app.events(run.run_id, context=context), required_tools=("investigate",)
        ).outcome
        == "unknown"
    )
    done = app.record(
        run.run_id,
        AgentEventKind.TOOL_SUCCEEDED,
        parent_id=start.event_id,
        tool_name="investigate",
        tool_version="v1",
        snapshot_id="s1",
        context=context,
    )
    app.record(run.run_id, AgentEventKind.RUN_COMPLETED, parent_id=done.event_id, context=context)
    events = app.events(run.run_id, context=context)
    result = evaluate_trajectory(run, events + (done,), required_tools=("investigate",))
    assert result.outcome == "pass" and result.tool_calls == 1
    assert (
        evaluate_trajectory(
            run, events + (replace(done, snapshot_id="other"),), required_tools=("investigate",)
        ).outcome
        == "fail"
    )
    assert (
        evaluate_trajectory(
            run, tuple(e for e in events if e != done), required_tools=("investigate",)
        ).outcome
        == "unknown"
    )
    assert (
        evaluate_trajectory(
            run,
            events + (replace(done, event_id="foreign", run_id="foreign"),),
            required_tools=("investigate",),
        ).outcome
        == "fail"
    )
    report = summarize_trajectories((result,))
    assert report["counts"]["pass"] == 1 and report["live_counts"]["pass"] == 0
    assert "payload" not in event_dto(done) and "messages" not in event_dto(done)


def test_tool_error_never_satisfies_inspection(tmp_path: Path) -> None:
    context = RequestContext(
        "demo", "synthetic-tenant", "atlas", "lab", frozenset({Permission.READ_STATE}), "test"
    )
    app = AgentRunService(
        SqliteRunStore(tmp_path / "r.db"),
        versions=RunVersions("fixture", "none", "p", "t", "f", "a"),
        execution_kind=ExecutionKind.FIXTURE,
    )
    run = app.start(context=context)
    root = app.events(run.run_id, context=context)[0]
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=context,
    )
    failed = app.record(
        run.run_id,
        AgentEventKind.TOOL_FAILED,
        parent_id=start.event_id,
        tool_name="investigate",
        tool_version="v1",
        error_code="tool_timeout",
        context=context,
    )
    app.record(run.run_id, AgentEventKind.RUN_COMPLETED, parent_id=failed.event_id, context=context)
    assert (
        evaluate_trajectory(
            run, app.events(run.run_id, context=context), required_tools=("investigate",)
        ).outcome
        == "fail"
    )


def test_non_applicability_cannot_hide_failure_or_partial_execution(tmp_path: Path) -> None:
    context = RequestContext(
        "demo", "synthetic-tenant", "atlas", "lab", frozenset({Permission.READ_STATE}), "test"
    )
    app = AgentRunService(
        SqliteRunStore(tmp_path / "r.db"),
        versions=RunVersions("fixture", "none", "p", "t", "f", "a"),
        execution_kind=ExecutionKind.FIXTURE,
    )
    run = app.start(context=context)
    root = app.events(run.run_id, context=context)[0]
    assert (
        evaluate_trajectory(
            run, (root,), required_tools=(), non_applicable_reason="not requested"
        ).outcome
        == "not_applicable"
    )
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=context,
    )
    partial = evaluate_trajectory(
        run,
        app.events(run.run_id, context=context),
        required_tools=("investigate",),
        non_applicable_reason="not requested",
    )
    assert partial.outcome == "unknown", "partial execution erased by non-applicability"
    app.record(
        run.run_id,
        AgentEventKind.TOOL_FAILED,
        parent_id=start.event_id,
        tool_name="investigate",
        tool_version="v1",
        error_code="tool_timeout",
        context=context,
    )
    failed = evaluate_trajectory(
        run,
        app.events(run.run_id, context=context),
        required_tools=("investigate",),
        non_applicable_reason="not requested",
    )
    assert failed.outcome == "fail", "observed failure erased by non-applicability"
    assert failed.tool_calls == 1


def test_terminal_event_cannot_precede_or_bypass_recorded_result(tmp_path: Path) -> None:
    from datetime import timedelta

    from procurement_intelligence_lab.platform.semantics.agent_runs import AgentEvent

    context = RequestContext(
        "demo", "synthetic-tenant", "atlas", "lab", frozenset({Permission.READ_STATE}), "test"
    )
    app = AgentRunService(
        SqliteRunStore(tmp_path / "r.db"),
        versions=RunVersions("fixture", "none", "p", "t", "f", "a"),
        execution_kind=ExecutionKind.FIXTURE,
    )
    run = app.start(context=context)
    root = app.events(run.run_id, context=context)[0]
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=context,
    )
    done = app.record(
        run.run_id,
        AgentEventKind.TOOL_SUCCEEDED,
        parent_id=start.event_id,
        tool_name="investigate",
        tool_version="v1",
        snapshot_id="s",
        context=context,
    )
    events = app.events(run.run_id, context=context)
    for when in (root.occurred_at, done.occurred_at + timedelta(seconds=1)):
        terminal = AgentEvent(
            "terminal",
            run.run_id,
            run.query_id,
            run.attempt_id,
            when,
            AgentEventKind.RUN_COMPLETED,
            root.event_id,
        )
        assert (
            evaluate_trajectory(run, events + (terminal,), required_tools=("investigate",)).outcome
            == "fail"
        ), "terminal bypassed completed causal path"
