"""Authorized run creation and event recording, independent of orchestration."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEvent,
    AgentEventKind,
    AgentRun,
    ExecutionKind,
    RunConflict,
    RunVersions,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.ports.agent_runs import RunStore


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentRunService:
    def __init__(
        self,
        store: RunStore,
        *,
        versions: RunVersions,
        execution_kind: ExecutionKind,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.store = store
        self.versions = versions
        self.execution_kind = execution_kind
        self.clock = clock

    def _now(self) -> datetime:
        now = self.clock()
        if now.utcoffset() is None:
            raise ValueError("clock must return an aware timestamp")
        return now.astimezone(UTC)

    def start(self, *, context: RequestContext) -> AgentRun:
        context.require(Permission.READ_STATE)
        now = self._now()
        run = AgentRun(
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
            context.principal_id,
            context.tenant_id,
            context.project_id,
            context.site_id,
            now,
            self.execution_kind,
            self.versions,
        )
        initial = AgentEvent(
            str(uuid4()), run.run_id, run.query_id, run.attempt_id, now, AgentEventKind.RUN_STARTED
        )
        self.store.create(run, initial, context=context)
        return run

    def resume(self, run_id: str, *, context: RequestContext) -> AgentRun:
        context.require(Permission.READ_STATE)
        run = self.store.get(run_id, context=context)
        if run.execution_kind != self.execution_kind or run.versions != self.versions:
            raise RunConflict("resume configuration differs from immutable run")
        return run

    def events(self, run_id: str, *, context: RequestContext) -> tuple[AgentEvent, ...]:
        self.resume(run_id, context=context)
        return self.store.events(run_id, context=context)

    def recent(self, *, context: RequestContext, limit: int = 50) -> tuple[AgentRun, ...]:
        """Owned historical discovery; resume separately enforces current versions."""
        context.require(Permission.READ_STATE)
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("recent run limit must be an integer from 1 to 50")
        return self.store.recent(context=context, limit=limit)

    def record(
        self,
        run_id: str,
        kind: AgentEventKind,
        *,
        parent_id: str,
        context: RequestContext,
        tool_name: str | None = None,
        tool_version: str | None = None,
        snapshot_id: str | None = None,
        error_code: str | None = None,
    ) -> AgentEvent:
        run = self.resume(run_id, context=context)
        event = AgentEvent(
            str(uuid4()),
            run.run_id,
            run.query_id,
            run.attempt_id,
            self._now(),
            kind,
            parent_id,
            tool_name,
            tool_version,
            snapshot_id,
            error_code,
        )
        self.store.append(event, context=context)
        return event
