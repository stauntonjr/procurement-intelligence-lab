"""Two scoped operational tools over the same deterministic corpus services."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.corpus_investigation import (
    CorpusInvestigationService,
    InvestigationRequest,
    InvestigationResult,
)
from procurement_intelligence_lab.platform.semantics.agent_runs import AgentEventKind, RunConflict
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.ports.corpus import (
    CorpusAdmissionError,
    CorpusNotFoundError,
    CorpusSourceLookup,
    CorpusSourceRecord,
    CorpusSourceRow,
)

TOOL_SCHEMA_VERSION = "corpus-tools/v1"
Result = TypeVar("Result")


@dataclass(frozen=True)
class InvestigateToolArgs:
    request: InvestigationRequest

    @classmethod
    def from_mapping(cls, arguments: Mapping[str, object]) -> "InvestigateToolArgs":
        if set(arguments) != {"item", "as_of"}:
            raise ValueError("investigation accepts exactly item and as_of")
        item, cutoff = arguments["item"], arguments["as_of"]
        if not isinstance(item, str) or not isinstance(cutoff, str):
            raise TypeError("item and as_of must be strings")
        return cls(InvestigationRequest(item, datetime.fromisoformat(cutoff)))


@dataclass(frozen=True)
class SourceToolArgs:
    evidence_id: str

    def __post_init__(self) -> None:
        if type(self.evidence_id) is not str:
            raise TypeError("evidence_id must be a string")
        if not self.evidence_id.strip() or len(self.evidence_id) > 200:
            raise ValueError("evidence_id must be a nonempty bounded identifier")

    @classmethod
    def from_mapping(cls, arguments: Mapping[str, object]) -> "SourceToolArgs":
        if set(arguments) != {"evidence_id"} or not isinstance(arguments["evidence_id"], str):
            raise ValueError("source accepts exactly a string evidence_id")
        return cls(arguments["evidence_id"])


class ToolExecutionError(RuntimeError):
    """Closed public error catalog; raw document/provider errors are never exported."""

    def __init__(self, event_code: str) -> None:
        self.event_code = event_code
        self.code, self.category = {
            "corpus_admission_failed": (
                ErrorCode.AGENT_TOOL_ADMISSION_FAILED,
                ErrorCategory.INFRASTRUCTURE,
            ),
            "tool_timeout": (ErrorCode.AGENT_TOOL_TIMEOUT, ErrorCategory.TRANSIENT),
            "tool_unavailable": (ErrorCode.AGENT_TOOL_UNAVAILABLE, ErrorCategory.INFRASTRUCTURE),
            "invalid_tool_result": (ErrorCode.AGENT_TOOL_INVALID_RESULT, ErrorCategory.INPUT),
        }[event_code]
        super().__init__(self.code.value)

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "category": self.category.value}


@dataclass(frozen=True)
class CorpusAgentTools:
    investigator: CorpusInvestigationService
    lookup: CorpusSourceLookup
    runs: AgentRunService

    def _invoke(
        self,
        run_id: str,
        name: str,
        call: Callable[[], tuple[Result, str]],
        *,
        context: RequestContext,
    ) -> Result:
        run = self.runs.resume(run_id, context=context)
        if run.versions.tool_schema != TOOL_SCHEMA_VERSION:
            raise RunConflict("tool schema does not match recorded configuration")
        prior = self.runs.events(run_id, context=context)[-1]
        start = self.runs.record(
            run_id,
            AgentEventKind.TOOL_STARTED,
            parent_id=prior.event_id,
            tool_name=name,
            tool_version=TOOL_SCHEMA_VERSION,
            context=context,
        )
        try:
            result, snapshot = call()
        except Exception as error:
            if isinstance(error, CorpusAdmissionError):
                code = "corpus_admission_failed"
            elif isinstance(error, TimeoutError):
                code = "tool_timeout"
            elif isinstance(
                error,
                (
                    CorpusAdmissionError,
                    CorpusNotFoundError,
                    ValueError,
                    TypeError,
                    AttributeError,
                    ScopeAuthorizationError,
                ),
            ):
                code = "invalid_tool_result"
            else:
                code = "tool_unavailable"
            self.runs.record(
                run_id,
                AgentEventKind.TOOL_FAILED,
                parent_id=start.event_id,
                tool_name=name,
                tool_version=TOOL_SCHEMA_VERSION,
                error_code=code,
                context=context,
            )
            if isinstance(error, ScopeAuthorizationError):
                raise
            raise ToolExecutionError(code) from error
        self.runs.record(
            run_id,
            AgentEventKind.TOOL_SUCCEEDED,
            parent_id=start.event_id,
            tool_name=name,
            tool_version=TOOL_SCHEMA_VERSION,
            snapshot_id=snapshot,
            context=context,
        )
        return result

    def investigate(
        self, run_id: str, arguments: InvestigateToolArgs, *, context: RequestContext
    ) -> InvestigationResult:
        context.require(Permission.READ_STATE)

        def call() -> tuple[InvestigationResult, str]:
            result = self.investigator.investigate(arguments.request, context=context)
            return result, result.snapshot_id

        return self._invoke(run_id, "investigate_quantity", call, context=context)

    def source(
        self, run_id: str, arguments: SourceToolArgs, *, context: RequestContext
    ) -> CorpusSourceRow | CorpusSourceRecord:
        context.require(Permission.READ_EVIDENCE)

        def call() -> tuple[CorpusSourceRow | CorpusSourceRecord, str]:
            result = self.lookup.source_by_id(arguments.evidence_id, context=context)
            return result, stable_id(
                "source-inspection",
                context.tenant_id,
                context.project_id,
                context.site_id,
                result.evidence.as_dict(),
            )

        return self._invoke(run_id, "inspect_source", call, context=context)
