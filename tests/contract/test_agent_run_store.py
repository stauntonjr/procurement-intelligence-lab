"""Run isolation and durable audit behavior across storage lifetimes."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.sqlite_agent_runs import SqliteRunStore
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEventKind,
    ExecutionKind,
    RunConflict,
    RunNotFound,
    RunVersions,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)

CONTEXT = RequestContext(
    "demo", "synthetic-tenant", "atlas", "lab", frozenset({Permission.READ_STATE}), "test"
)
NOW = datetime(2026, 10, 3, tzinfo=UTC)
VERSIONS = RunVersions("fixture", "none", "prompt/v1", "tools/v1", "corpus/v1", "app/v1")


def service(path: Path) -> AgentRunService:
    return AgentRunService(
        SqliteRunStore(path),
        versions=VERSIONS,
        execution_kind=ExecutionKind.FIXTURE,
        clock=lambda: NOW,
    )


def test_fresh_examples_and_reopened_resume(tmp_path: Path) -> None:
    first = service(tmp_path / "runs.db").start(context=CONTEXT)
    second = service(tmp_path / "runs.db").start(context=CONTEXT)
    assert first.run_id != second.run_id and first.thread_id != second.thread_id
    assert first.query_id != second.query_id and first.attempt_id != second.attempt_id
    assert service(tmp_path / "runs.db").resume(first.run_id, context=CONTEXT) == first
    for context in (replace(CONTEXT, project_id="delta"), replace(CONTEXT, principal_id="other")):
        with pytest.raises(RunNotFound):
            service(tmp_path / "runs.db").resume(first.run_id, context=context)
    with pytest.raises(ScopeAuthorizationError):
        service(tmp_path / "runs.db").resume(
            first.run_id, context=replace(CONTEXT, permissions=frozenset())
        )


def test_events_exact_replay_conflict_and_causal_boundaries(tmp_path: Path) -> None:
    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=CONTEXT,
    )
    done = app.record(
        run.run_id,
        AgentEventKind.TOOL_SUCCEEDED,
        parent_id=start.event_id,
        tool_name="investigate",
        tool_version="v1",
        snapshot_id="snapshot:v1",
        context=CONTEXT,
    )
    app.store.append(done, context=CONTEXT)
    assert len(app.events(run.run_id, context=CONTEXT)) == 3
    for event in (
        replace(done, snapshot_id="changed"),
        replace(done, event_id="foreign", run_id="missing"),
        replace(done, event_id="wrong-attempt", attempt_id="foreign"),
        replace(done, event_id="wrong-time", occurred_at=NOW - timedelta(seconds=1)),
        replace(done, event_id="wrong-parent", parent_id=root.event_id),
        replace(done, event_id="wrong-tool", tool_name="other"),
    ):
        with pytest.raises((RunConflict, RunNotFound, ValueError)):
            app.store.append(event, context=CONTEXT)


def test_concurrent_exact_replay_has_one_event(tmp_path: Path) -> None:
    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    event = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="investigate",
        tool_version="v1",
        context=CONTEXT,
    )

    def replay(_: int) -> None:
        SqliteRunStore(tmp_path / "runs.db").append(event, context=CONTEXT)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(replay, range(8)))
    assert len(app.events(run.run_id, context=CONTEXT)) == 2


def test_invalid_schema_and_corruption_are_storage_failures(tmp_path: Path) -> None:
    import sqlite3

    from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError

    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    with sqlite3.connect(tmp_path / "runs.db") as db:
        db.execute("UPDATE agent_runs SET payload='[]' WHERE run_id=?", (run.run_id,))
    with pytest.raises(RunStoreError):
        app.resume(run.run_id, context=CONTEXT)
    with sqlite3.connect(tmp_path / "runs.db") as db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(RunStoreError):
        SqliteRunStore(tmp_path / "runs.db")


def test_start_replay_cannot_change_metadata(tmp_path: Path) -> None:
    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    with pytest.raises(RunConflict):
        app.store.create(
            replace(run, versions=replace(VERSIONS, model="changed")), root, context=CONTEXT
        )
    assert app.resume(run.run_id, context=CONTEXT).versions == VERSIONS


def test_invalid_clock_and_tool_completion_fail_closed(tmp_path: Path) -> None:
    app = AgentRunService(
        SqliteRunStore(tmp_path / "runs.db"),
        versions=VERSIONS,
        execution_kind=ExecutionKind.FIXTURE,
        clock=lambda: NOW.replace(tzinfo=None),
    )
    with pytest.raises(ValueError):
        app.start(context=CONTEXT)
    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="inspect",
        tool_version="v1",
        context=CONTEXT,
    )
    with pytest.raises(RunConflict):
        app.record(
            run.run_id, AgentEventKind.RUN_COMPLETED, parent_id=start.event_id, context=CONTEXT
        )
    with pytest.raises(ValueError):
        app.record(
            run.run_id,
            AgentEventKind.TOOL_SUCCEEDED,
            parent_id=start.event_id,
            tool_name="inspect",
            tool_version="v1",
            context=CONTEXT,
        )


def test_permission_is_checked_before_store_read(tmp_path: Path) -> None:
    from unittest.mock import Mock

    store = Mock()
    app = AgentRunService(store, versions=VERSIONS, execution_kind=ExecutionKind.FIXTURE)
    with pytest.raises(ScopeAuthorizationError):
        app.resume("run", context=replace(CONTEXT, permissions=frozenset()))
    store.get.assert_not_called()


@pytest.mark.parametrize(
    "field",
    ["provider", "model", "prompt", "tool_schema", "fixture", "application", "execution_kind"],
)
def test_resume_rejects_changed_execution_configuration(tmp_path: Path, field: str) -> None:
    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    versions = VERSIONS if field == "execution_kind" else replace(VERSIONS, **{field: "changed"})
    other = AgentRunService(
        SqliteRunStore(tmp_path / "runs.db"),
        versions=versions,
        execution_kind=ExecutionKind.LIVE if field == "execution_kind" else ExecutionKind.FIXTURE,
    )
    with pytest.raises(RunConflict):
        other.resume(run.run_id, context=CONTEXT)
    with pytest.raises(RunConflict):
        other.record(
            run.run_id,
            AgentEventKind.RUN_COMPLETED,
            parent_id=app.events(run.run_id, context=CONTEXT)[0].event_id,
            context=CONTEXT,
        )
    assert len(app.events(run.run_id, context=CONTEXT)) == 1


def test_fixture_cannot_write_live_ledger(tmp_path: Path) -> None:
    live = AgentRunService(
        SqliteRunStore(tmp_path / "runs.db"), versions=VERSIONS, execution_kind=ExecutionKind.LIVE
    )
    run = live.start(context=CONTEXT)
    with pytest.raises(RunConflict):
        service(tmp_path / "runs.db").resume(run.run_id, context=CONTEXT)


@pytest.mark.parametrize(
    "payload",
    [{"prompt": "synthetic-private", "credentials": "synthetic-secret"}, ["payload"], 12, True],
)
def test_arbitrary_event_and_version_fields_rejected(tmp_path: Path, payload: object) -> None:
    from typing import cast

    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    start = app.record(
        run.run_id,
        AgentEventKind.TOOL_STARTED,
        parent_id=root.event_id,
        tool_name="inspect",
        tool_version="v1",
        context=CONTEXT,
    )
    with pytest.raises((ValueError, TypeError)):
        app.record(
            run.run_id,
            AgentEventKind.TOOL_SUCCEEDED,
            parent_id=start.event_id,
            tool_name="inspect",
            tool_version="v1",
            snapshot_id=cast(str, payload),
            context=CONTEXT,
        )
    with pytest.raises((ValueError, TypeError)):
        replace(VERSIONS, model=cast(str, payload))
    for field in (
        "event_id",
        "run_id",
        "query_id",
        "attempt_id",
        "parent_id",
        "tool_name",
        "tool_version",
        "error_code",
    ):
        with pytest.raises((ValueError, TypeError)):
            replace(start, **{field: cast(str, payload)})
    assert len(app.events(run.run_id, context=CONTEXT)) == 2


def test_unsupported_event_enum_is_rejected(tmp_path: Path) -> None:
    from enum import StrEnum
    from typing import cast

    class Unsupported(StrEnum):
        PAYLOAD = "arbitrary_payload"

    app = service(tmp_path / "runs.db")
    run = app.start(context=CONTEXT)
    root = app.events(run.run_id, context=CONTEXT)[0]
    with pytest.raises((ValueError, TypeError)):
        replace(root, kind=cast(AgentEventKind, Unsupported.PAYLOAD))
