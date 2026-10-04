"""Optional serial checkpoint mechanics; application ledgers retain authority."""

# LangGraph's shipped overloads contain unknown generics and two modules omit py.typed.
# Keep this accommodation local to the framework boundary; repository contracts stay strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypedDict, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, StateSnapshot, interrupt
from langsmith import tracing_context  # pyright: ignore[reportUnknownVariableType]

from procurement_intelligence_lab.application.corpus_agent_tools import InvestigateToolArgs
from procurement_intelligence_lab.application.exact_brief_review import BriefReviewService
from procurement_intelligence_lab.platform.semantics.agent_runs import AgentEventKind, ExecutionKind
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefNotFound,
    ReviewBrief,
    ReviewReceipt,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.platform.semantics.workflows import (
    WorkflowBudgetExceeded,
    WorkflowError,
    WorkflowRequest,
    WorkflowView,
)


class _State(TypedDict):
    run_id: str
    item: str
    as_of: str
    brief_id: str
    digest: str
    snapshot_id: str
    decision: str
    done: bool


@dataclass(frozen=True)
class _Invocation:
    context: RequestContext
    deadline: float
    receipt: ReviewReceipt | None = None

    def check(self) -> None:
        if time.monotonic() >= self.deadline:
            raise WorkflowBudgetExceeded("invocation deadline exceeded")


Graph = CompiledStateGraph[_State, _Invocation, _State, _State]


def _route(state: _State) -> str:
    return "save" if state["decision"] == "approve" else "complete"


class LangGraphReviewRuntime:
    def __init__(
        self,
        service: BriefReviewService,
        database: Path,
        *,
        max_steps: int = 8,
        timeout_seconds: float = 30,
    ) -> None:
        if type(max_steps) is not int or not 4 <= max_steps <= 32:
            raise ValueError("step ceiling must be an integer in [4,32]")
        if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 120:
            raise ValueError("deadline must be finite and in (0,120]")
        if service.tools.runs.execution_kind not in (ExecutionKind.FIXTURE, ExecutionKind.LIVE):
            raise ValueError("review runtime supports fixture or live execution only")
        self.service = service
        self.database = database
        self.checkpoint_path = database.with_name(database.name + ".checkpoints.sqlite")
        self.lock_path = database.with_name(database.name + ".workflow-lock.sqlite")
        self.max_steps = max_steps
        self.timeout_seconds = float(timeout_seconds)

    @staticmethod
    def _operational(context: RequestContext) -> RequestContext:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        return replace(
            context, permissions=frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE})
        )

    def _config(self, run_id: str, context: RequestContext) -> RunnableConfig:
        # This must precede opening/deserializing any checkpoint database.
        run = self.service.tools.runs.resume(run_id, context=self._operational(context))
        return {"configurable": {"thread_id": run.thread_id}, "recursion_limit": self.max_steps}

    @contextmanager
    def _graph(self) -> Generator[Graph]:
        """Bounded cross-process serialization, separate from application/checkpoint writes."""
        try:
            lock = sqlite3.connect(self.lock_path, timeout=min(5, self.timeout_seconds))
            try:
                lock.execute("CREATE TABLE IF NOT EXISTS coordinator (id INTEGER PRIMARY KEY)")
                lock.commit()
                lock.execute("BEGIN IMMEDIATE")
                connection = sqlite3.connect(self.checkpoint_path, check_same_thread=False)
                try:
                    builder = StateGraph(_State, context_schema=_Invocation)
                    builder.add_node("draft", self._draft)
                    builder.add_node("review", self._review)
                    builder.add_node("save", self._save)
                    builder.add_node("complete", self._complete)
                    builder.add_edge(START, "draft")
                    builder.add_edge("draft", "review")
                    builder.add_conditional_edges("review", _route)
                    builder.add_edge("save", "complete")
                    builder.add_edge("complete", END)
                    # No trace upload is authorized, including environment-enabled tracing.
                    with tracing_context(enabled=False):
                        yield builder.compile(checkpointer=SqliteSaver(connection))
                finally:
                    connection.close()
            finally:
                lock.close()
        except sqlite3.Error as error:
            raise WorkflowError("workflow checkpoint/coordinator unavailable") from error
        except GraphRecursionError as error:
            raise WorkflowBudgetExceeded("workflow step ceiling exceeded") from error

    @staticmethod
    def _snapshot(graph: Graph, config: RunnableConfig) -> StateSnapshot:
        # Only the framework storage read is inside this boundary. Application policy calls
        # remain outside, preserving their typed authorization/conflict failures.
        try:
            return graph.get_state(config)
        except Exception as error:
            raise WorkflowError("checkpoint decoding/schema integrity failed") from error

    def _draft(self, state: _State, runtime: Runtime[_Invocation]) -> dict[str, object]:
        invocation = runtime.context
        invocation.check()
        context = self._operational(invocation.context)
        args = InvestigateToolArgs.from_mapping({"item": state["item"], "as_of": state["as_of"]})
        # A crash after durable draft but before checkpoint acknowledgment must not redraft.
        try:
            brief = self.service.get(state["run_id"], None, context=context)
        except BriefNotFound:
            brief = self.service.draft(state["run_id"], args, context=context)
        if (brief.item, brief.as_of) != (args.request.canonical_key, args.request.as_of):
            raise BriefConflict("recovered draft differs from original request")
        invocation.check()
        return {
            "brief_id": brief.brief_id,
            "digest": brief.digest,
            "snapshot_id": brief.snapshot_id,
        }

    def _bound_brief(self, state: _State, context: RequestContext) -> ReviewBrief:
        try:
            brief = self.service.get(state["run_id"], state["brief_id"], context=context)
            args = InvestigateToolArgs.from_mapping(
                {"item": state["item"], "as_of": state["as_of"]}
            )
            if (brief.digest, brief.snapshot_id, brief.item, brief.as_of) != (
                state["digest"],
                state["snapshot_id"],
                args.request.canonical_key,
                args.request.as_of,
            ):
                raise WorkflowError("checkpoint differs from immutable brief")
            if self.service.get(state["run_id"], None, context=context) != brief:
                raise BriefConflict("checkpoint brief is no longer active")
            return brief
        except BriefConflict:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise WorkflowError("malformed checkpoint binding") from error

    def _review(self, state: _State, runtime: Runtime[_Invocation]) -> dict[str, object]:
        invocation = runtime.context
        invocation.check()
        brief = self._bound_brief(state, self._operational(invocation.context))
        # No side effects before interrupt: this node runs again on resume.
        receipt_brief_id = interrupt(
            {"brief_id": brief.brief_id, "digest": brief.digest, "snapshot_id": brief.snapshot_id}
        )
        receipt = invocation.receipt
        if (
            receipt is None
            or receipt_brief_id != receipt.brief_id
            or (receipt.brief_id, receipt.run_id, receipt.digest, receipt.reviewer_id)
            != (brief.brief_id, brief.run.run_id, brief.digest, invocation.context.principal_id)
        ):
            raise BriefConflict("resume lacks trusted application review receipt")
        invocation.check()
        return {"decision": receipt.decision}

    def _save(self, state: _State, runtime: Runtime[_Invocation]) -> dict[str, object]:
        invocation = runtime.context
        invocation.check()
        brief = self._bound_brief(state, self._operational(invocation.context))
        receipt = invocation.receipt
        if (
            receipt is None
            or receipt.decision != "approve"
            or (receipt.run_id, receipt.brief_id, receipt.digest)
            != (brief.run.run_id, brief.brief_id, brief.digest)
        ):
            raise BriefConflict("save requires trusted approval for exact brief")
        self.service.save(
            brief.run.run_id,
            brief.brief_id,
            brief.digest,
            brief.idempotency_key,
            context=invocation.context,
        )
        invocation.check()
        return {}

    def _complete(self, state: _State, runtime: Runtime[_Invocation]) -> dict[str, object]:
        runtime.context.check()
        context = self._operational(runtime.context.context)
        brief = self._bound_brief(state, context)
        receipt = self.service.receipt(state["run_id"], brief.brief_id, context=context)
        if receipt is None or receipt.decision != state["decision"]:
            raise WorkflowError("checkpoint decision lacks matching durable receipt")
        if (
            state["decision"] == "approve"
            and self.service.saved(state["run_id"], brief.brief_id, context=context) is None
        ):
            raise WorkflowError("checkpoint cannot fabricate a saved result")
        runs = self.service.tools.runs
        events = runs.events(state["run_id"], context=context)
        if events[-1].kind != AgentEventKind.RUN_COMPLETED:
            runs.record(
                state["run_id"],
                AgentEventKind.RUN_COMPLETED,
                parent_id=events[-1].event_id,
                context=context,
            )
        return {"done": True}

    def _view(self, run_id: str, snapshot: StateSnapshot, context: RequestContext) -> WorkflowView:
        state = cast(_State, snapshot.values)
        if not state or state.get("run_id") != run_id:
            raise WorkflowError("owned run has no matching workflow checkpoint")
        brief = self._bound_brief(state, self._operational(context))
        saved = self.service.saved(run_id, brief.brief_id, context=context)
        if state.get("done"):
            receipt = self.service.receipt(run_id, brief.brief_id, context=context)
            if receipt is None or receipt.decision != state["decision"]:
                raise WorkflowError("terminal checkpoint has no matching review receipt")
            if snapshot.next or state.get("decision") not in ("approve", "reject"):
                raise WorkflowError("invalid terminal checkpoint")
            if state["decision"] == "approve":
                if saved is None:
                    raise WorkflowError("completed checkpoint has no durable saved result")
                return WorkflowView(run_id, "completed", brief, saved)
            if saved is not None:
                raise WorkflowError("rejected checkpoint conflicts with saved result")
            return WorkflowView(run_id, "rejected", brief, None)
        if snapshot.next == ("review",):
            return WorkflowView(run_id, "awaiting_review", brief, None)
        if snapshot.next in (("save",), ("complete",)):
            return WorkflowView(run_id, "ready_to_save", brief, saved)
        raise WorkflowError("unsupported checkpoint lifecycle")

    def start(self, request: WorkflowRequest, *, context: RequestContext) -> WorkflowView:
        operational = self._operational(context)
        run = self.service.tools.runs.start(context=operational)
        return self.begin(run.run_id, request, context=operational)

    def begin(
        self, run_id: str, request: WorkflowRequest, *, context: RequestContext
    ) -> WorkflowView:
        operational = self._operational(context)
        run = self.service.tools.runs.resume(run_id, context=operational)
        config = self._config(run.run_id, operational)
        with self._graph() as graph:
            snapshot = self._snapshot(graph, config)
            if snapshot.values:
                state = snapshot.values
                if state.get("run_id") != run_id:
                    raise WorkflowError("checkpoint run differs from authorized run")
                if (
                    state.get("item") != request.item
                    or state.get("as_of") != request.as_of.isoformat()
                ):
                    raise BriefConflict("existing workflow request differs")
                if snapshot.next == ("draft",):
                    graph.invoke(
                        None,
                        config,
                        context=_Invocation(operational, time.monotonic() + self.timeout_seconds),
                    )
                return self._view(run_id, self._snapshot(graph, config), operational)
            graph.invoke(
                {
                    "run_id": run.run_id,
                    "item": request.item,
                    "as_of": request.as_of.isoformat(),
                    "brief_id": "",
                    "digest": "",
                    "snapshot_id": "",
                    "decision": "",
                    "done": False,
                },
                config,
                context=_Invocation(operational, time.monotonic() + self.timeout_seconds),
            )
            return self._view(run.run_id, self._snapshot(graph, config), operational)

    def status(self, run_id: str, *, context: RequestContext) -> WorkflowView:
        config = self._config(run_id, context)
        with self._graph() as graph:
            return self._view(run_id, self._snapshot(graph, config), context)

    def recover(self, run_id: str, *, context: RequestContext) -> WorkflowView:
        operational = self._operational(context)
        config = self._config(run_id, operational)
        with self._graph() as graph:
            snapshot = self._snapshot(graph, config)
            if not snapshot.values or snapshot.values.get("run_id") != run_id:
                raise WorkflowError("run has no matching recovery checkpoint")
            if snapshot.next == ("draft",):
                graph.invoke(
                    None,
                    config,
                    context=_Invocation(operational, time.monotonic() + self.timeout_seconds),
                )
            return self._view(run_id, self._snapshot(graph, config), operational)

    def review(
        self, run_id: str, brief_id: str, digest: str, decision: str, *, context: RequestContext
    ) -> WorkflowView:
        context.require(Permission.REVIEW)
        if decision == "approve":
            context.require(Permission.ACT)
        config = self._config(run_id, context)
        with self._graph() as graph:
            snapshot = self._snapshot(graph, config)
            view = self._view(run_id, snapshot, context)
            if (brief_id, digest) != (view.brief.brief_id, view.brief.digest):
                raise BriefConflict("review differs from checkpoint exact brief")
            receipt = self.service.review(run_id, brief_id, digest, decision, context=context)
            if snapshot.next:
                value = Command(resume=receipt.brief_id) if snapshot.next == ("review",) else None
                graph.invoke(
                    value,
                    config,
                    context=_Invocation(context, time.monotonic() + self.timeout_seconds, receipt),
                )
            elif decision == "approve":
                # Completed checkpoint replay is still an action acknowledgment. Preserve
                # the same current-evidence checks as an idempotent save during recovery.
                self.service.save(
                    run_id, brief_id, digest, view.brief.idempotency_key, context=context
                )
            return self._view(run_id, self._snapshot(graph, config), context)
