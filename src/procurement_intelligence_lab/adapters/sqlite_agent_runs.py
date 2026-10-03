"""Local durable run ledger with scoped reads and atomic event replay."""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEvent,
    AgentEventKind,
    AgentRun,
    ExecutionKind,
    RunConflict,
    RunNotFound,
    RunVersions,
    event_dto,
    run_dto,
    validate_event,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


class RunStoreError(RuntimeError):
    """Storage is unavailable or cannot satisfy the supported schema."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.AGENT_RUN_STORE_UNAVAILABLE

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "category": self.category.value, "message": str(self)}


def _text(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value:
        raise RunStoreError("invalid stored field")
    return value


def _optional(data: dict[str, Any], key: str) -> str | None:
    return None if data[key] is None else _text(data, key)


def _run(raw: str) -> AgentRun:
    try:
        data: dict[str, Any] = json.loads(raw)
        versions: dict[str, Any] = data["versions"]
        return AgentRun(
            run_id=_text(data, "run_id"),
            query_id=_text(data, "query_id"),
            attempt_id=_text(data, "attempt_id"),
            thread_id=_text(data, "thread_id"),
            principal_id=_text(data, "principal_id"),
            tenant_id=_text(data, "tenant_id"),
            project_id=_text(data, "project_id"),
            site_id=_text(data, "site_id"),
            created_at=datetime.fromisoformat(_text(data, "created_at")),
            execution_kind=ExecutionKind(_text(data, "execution_kind")),
            versions=RunVersions(
                _text(versions, "provider"),
                _text(versions, "model"),
                _text(versions, "prompt"),
                _text(versions, "tool_schema"),
                _text(versions, "fixture"),
                _text(versions, "application"),
            ),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise RunStoreError("invalid stored run") from error


def _event(raw: str) -> AgentEvent:
    try:
        data: dict[str, Any] = json.loads(raw)
        return AgentEvent(
            event_id=_text(data, "event_id"),
            run_id=_text(data, "run_id"),
            query_id=_text(data, "query_id"),
            attempt_id=_text(data, "attempt_id"),
            occurred_at=datetime.fromisoformat(_text(data, "occurred_at")),
            kind=AgentEventKind(_text(data, "kind")),
            parent_id=_optional(data, "parent_id"),
            tool_name=_optional(data, "tool_name"),
            tool_version=_optional(data, "tool_version"),
            snapshot_id=_optional(data, "snapshot_id"),
            error_code=_optional(data, "error_code"),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise RunStoreError("invalid stored event") from error


class SqliteRunStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RunStoreError("unsupported run database schema")
            db.execute(
                "CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT PRIMARY KEY, query_id TEXT UNIQUE NOT NULL, attempt_id TEXT UNIQUE NOT NULL, thread_id TEXT UNIQUE NOT NULL, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, site_id TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS agent_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, run_id TEXT NOT NULL REFERENCES agent_runs(run_id), payload TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version = 1")

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self.path, timeout=5)
            try:
                db.execute("PRAGMA foreign_keys = ON")
                with db:
                    yield db
            finally:
                db.close()
        except sqlite3.Error as error:
            raise RunStoreError("run database operation failed") from error

    @staticmethod
    def _get(db: sqlite3.Connection, run_id: str, context: RequestContext) -> AgentRun:
        context.require(Permission.READ_STATE)
        row = db.execute(
            "SELECT payload FROM agent_runs WHERE run_id=? AND principal_id=? AND tenant_id=? AND project_id=? AND site_id=?",
            (run_id, context.principal_id, context.tenant_id, context.project_id, context.site_id),
        ).fetchone()
        if row is None:
            raise RunNotFound("run not found in authorized owner scope")
        return _run(cast(str, row[0]))

    @staticmethod
    def _events(db: sqlite3.Connection, run_id: str) -> tuple[AgentEvent, ...]:
        return tuple(
            _event(cast(str, row[0]))
            for row in db.execute(
                "SELECT payload FROM agent_events WHERE run_id=? ORDER BY sequence", (run_id,)
            )
        )

    def create(self, run: AgentRun, initial: AgentEvent, *, context: RequestContext) -> None:
        context.require(Permission.READ_STATE)
        if (run.principal_id, run.tenant_id, run.project_id, run.site_id) != (
            context.principal_id,
            context.tenant_id,
            context.project_id,
            context.site_id,
        ):
            raise RunConflict("run owner differs from authorized caller")
        validate_event(run, (), initial)
        if initial.kind != AgentEventKind.RUN_STARTED:
            raise RunConflict("initial event must start run")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM agent_runs WHERE run_id=?", (run.run_id,)).fetchone():
                raise RunConflict("run already exists")
            db.execute(
                "INSERT INTO agent_runs VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    run.run_id,
                    run.query_id,
                    run.attempt_id,
                    run.thread_id,
                    run.principal_id,
                    run.tenant_id,
                    run.project_id,
                    run.site_id,
                    json.dumps(run_dto(run), sort_keys=True),
                ),
            )
            db.execute(
                "INSERT INTO agent_events (event_id,run_id,payload) VALUES (?,?,?)",
                (initial.event_id, run.run_id, json.dumps(event_dto(initial), sort_keys=True)),
            )

    def get(self, run_id: str, *, context: RequestContext) -> AgentRun:
        context.require(Permission.READ_STATE)
        with self._connection() as db:
            return self._get(db, run_id, context)

    def events(self, run_id: str, *, context: RequestContext) -> tuple[AgentEvent, ...]:
        context.require(Permission.READ_STATE)
        with self._connection() as db:
            self._get(db, run_id, context)
            return self._events(db, run_id)

    def append(self, event: AgentEvent, *, context: RequestContext) -> None:
        context.require(Permission.READ_STATE)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._get(db, event.run_id, context)
            existing = self._events(db, run.run_id)
            prior = next((e for e in existing if e.event_id == event.event_id), None)
            if prior is not None:
                if prior != event:
                    raise RunConflict("event replay changed content")
                return
            validate_event(run, existing, event)
            if db.execute(
                "SELECT 1 FROM agent_events WHERE event_id=?", (event.event_id,)
            ).fetchone():
                raise RunConflict("event identity already belongs to another run")
            db.execute(
                "INSERT INTO agent_events (event_id,run_id,payload) VALUES (?,?,?)",
                (event.event_id, run.run_id, json.dumps(event_dto(event), sort_keys=True)),
            )
