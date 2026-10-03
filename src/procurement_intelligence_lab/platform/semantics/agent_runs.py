"""Framework-independent run identity and explicit audit event contracts."""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
    SemanticTypeContractError,
)


def _identifier(value: object) -> None:
    if not isinstance(value, str):
        raise SemanticTypeContractError("identity fields must be strings")
    if not value.strip() or len(value) > 200:
        raise SemanticContractError("nonempty bounded identities are required")


def _aware(value: object) -> None:
    if not isinstance(value, datetime):
        raise SemanticTypeContractError("timestamp must be a datetime")
    if value.utcoffset() is None:
        raise SemanticContractError("timestamp must be timezone aware")


class RunNotFound(LookupError):
    """No run is available within the authorized owner scope."""

    category = ErrorCategory.INPUT
    code = ErrorCode.AGENT_RUN_NOT_FOUND

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "category": self.category.value, "message": str(self)}


class RunConflict(SemanticContractError):
    """Replay or event lifecycle contradicts immutable recorded state."""

    category = ErrorCategory.POLICY
    code = ErrorCode.AGENT_RUN_CONFLICT


class ExecutionKind(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"
    REPLAY = "replay"


class AgentEventKind(StrEnum):
    RUN_STARTED = "run_started"
    TOOL_STARTED = "tool_started"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    RUN_COMPLETED = "run_completed"


@dataclass(frozen=True)
class RunVersions:
    provider: str
    model: str
    prompt: str
    tool_schema: str
    fixture: str
    application: str

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            _identifier(value)


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    query_id: str
    attempt_id: str
    thread_id: str
    principal_id: str
    tenant_id: str
    project_id: str
    site_id: str
    created_at: datetime
    execution_kind: ExecutionKind
    versions: RunVersions

    def __post_init__(self) -> None:
        for value in (
            self.run_id,
            self.query_id,
            self.attempt_id,
            self.thread_id,
            self.principal_id,
            self.tenant_id,
            self.project_id,
            self.site_id,
        ):
            _identifier(value)
        _aware(self.created_at)
        if type(self.execution_kind) is not ExecutionKind or type(self.versions) is not RunVersions:
            raise SemanticTypeContractError("supported execution kind and versions are required")


@dataclass(frozen=True)
class AgentEvent:
    event_id: str
    run_id: str
    query_id: str
    attempt_id: str
    occurred_at: datetime
    kind: AgentEventKind
    parent_id: str | None = None
    tool_name: str | None = None
    tool_version: str | None = None
    snapshot_id: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        for value in (self.event_id, self.run_id, self.query_id, self.attempt_id):
            _identifier(value)
        for value in (
            self.parent_id,
            self.tool_name,
            self.tool_version,
            self.snapshot_id,
            self.error_code,
        ):
            if value is not None:
                _identifier(value)
        _aware(self.occurred_at)
        if type(self.kind) is not AgentEventKind:
            raise SemanticTypeContractError("unsupported event kind")
        tool = self.kind in (
            AgentEventKind.TOOL_STARTED,
            AgentEventKind.TOOL_SUCCEEDED,
            AgentEventKind.TOOL_FAILED,
        )
        if tool != bool(self.tool_name and self.tool_version):
            raise SemanticContractError("tool events require tool name and version")
        if not tool and (self.tool_name is not None or self.tool_version is not None):
            raise SemanticContractError("non-tool event cannot contain tool fields")
        if (self.kind == AgentEventKind.TOOL_SUCCEEDED) != bool(self.snapshot_id):
            raise SemanticContractError("successful tool event requires snapshot identity only")
        if self.kind == AgentEventKind.TOOL_FAILED:
            if self.error_code not in ("tool_timeout", "tool_unavailable", "invalid_tool_result"):
                raise SemanticContractError("unsupported tool failure code")
        elif self.error_code is not None:
            raise SemanticContractError("error code is only valid on tool failure")


def validate_event(run: AgentRun, existing: tuple[AgentEvent, ...], event: AgentEvent) -> None:
    """Validate positive causal evidence before durable append or trajectory scoring."""
    if (event.run_id, event.query_id, event.attempt_id) != (
        run.run_id,
        run.query_id,
        run.attempt_id,
    ):
        raise RunConflict("event belongs to another execution")
    if event.occurred_at < run.created_at:
        raise RunConflict("event predates run")
    if event.kind == AgentEventKind.RUN_STARTED:
        if existing or event.parent_id is not None or event.occurred_at != run.created_at:
            raise RunConflict("run start must be first and match creation")
        return
    if any(e.kind == AgentEventKind.RUN_COMPLETED for e in existing):
        raise RunConflict("run is terminal")
    parent = next((e for e in existing if e.event_id == event.parent_id), None)
    if parent is None or event.occurred_at < parent.occurred_at:
        raise RunConflict("missing or future causal parent")
    if event.kind in (AgentEventKind.TOOL_SUCCEEDED, AgentEventKind.TOOL_FAILED):
        if parent.kind != AgentEventKind.TOOL_STARTED or (event.tool_name, event.tool_version) != (
            parent.tool_name,
            parent.tool_version,
        ):
            raise RunConflict("tool result does not match invocation")
        if any(
            e.parent_id == parent.event_id
            and e.kind in (AgentEventKind.TOOL_SUCCEEDED, AgentEventKind.TOOL_FAILED)
            for e in existing
        ):
            raise RunConflict("invocation already has a terminal result")
    if event.kind == AgentEventKind.RUN_COMPLETED:
        finished = {
            e.parent_id
            for e in existing
            if e.kind in (AgentEventKind.TOOL_SUCCEEDED, AgentEventKind.TOOL_FAILED)
        }
        if any(
            e.kind == AgentEventKind.TOOL_STARTED and e.event_id not in finished for e in existing
        ):
            raise RunConflict("cannot complete with pending tool calls")


def run_dto(run: AgentRun) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "query_id": run.query_id,
        "attempt_id": run.attempt_id,
        "thread_id": run.thread_id,
        "principal_id": run.principal_id,
        "tenant_id": run.tenant_id,
        "project_id": run.project_id,
        "site_id": run.site_id,
        "created_at": run.created_at.isoformat(),
        "execution_kind": run.execution_kind.value,
        "versions": asdict(run.versions),
    }


def event_dto(event: AgentEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "query_id": event.query_id,
        "attempt_id": event.attempt_id,
        "occurred_at": event.occurred_at.isoformat(),
        "kind": event.kind.value,
        "parent_id": event.parent_id,
        "tool_name": event.tool_name,
        "tool_version": event.tool_version,
        "snapshot_id": event.snapshot_id,
        "error_code": event.error_code,
    }
