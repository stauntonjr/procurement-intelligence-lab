"""Models propose intent; application binds scope and deterministic review facts."""

import time
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from typing import Protocol

from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.question_intent import canonical_item_mentions
from procurement_intelligence_lab.platform.semantics.agent_runs import ExecutionKind
from procurement_intelligence_lab.platform.semantics.interpretation import (
    InterpretationCall,
    ModelFailure,
    ModelReply,
    QuestionProposal,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.platform.semantics.workflows import WorkflowRequest, WorkflowView
from procurement_intelligence_lab.ports.interpretation import (
    InterpretationStore,
    QuestionInterpreter,
)
from procurement_intelligence_lab.ports.review_sources import ReviewSources
from procurement_intelligence_lab.ports.workflows import AgentWorkflowRuntime


class QuestionComposition(Protocol):
    @property
    def runs(self) -> AgentRunService: ...
    @property
    def reader(self) -> ReviewSources: ...
    @property
    def runtime(self) -> AgentWorkflowRuntime: ...


@dataclass(frozen=True)
class QuestionOutcome:
    call: InterpretationCall
    view: WorkflowView | None


@dataclass(frozen=True)
class QuestionReviewService:
    composition: QuestionComposition
    model: QuestionInterpreter
    store: InterpretationStore

    def ask(self, question: str, as_of: datetime, *, context: RequestContext) -> QuestionOutcome:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        if self.composition.runs.execution_kind != ExecutionKind.LIVE:
            raise ValueError("live interpretation requires live run configuration")
        if type(question) is not str or not question.strip() or len(question) > 1000:
            raise ValueError("question must contain 1..1000 characters")
        WorkflowRequest("validate", as_of)
        # Admit scoped catalog before creating a call; no gold/case labels enter the prompt.
        items = tuple(sorted(set(self.composition.reader.items(context=context))))
        run = self.composition.runs.start(context=context)
        call = InterpretationCall(run.run_id, sha256(question.encode()).hexdigest(), as_of)
        self.store.create(call)
        began = time.monotonic()
        reply: ModelReply | None = None
        try:
            reply = self.model.interpret(question, items, context.project_id, as_of.isoformat())
            proposal = QuestionProposal.parse(reply.text)
            if proposal.project != context.project_id or (
                proposal.status == "investigate"
                and (
                    proposal.item not in items
                    or canonical_item_mentions(question, items) != (proposal.item,)
                    or proposal.as_of != as_of
                )
            ):
                raise ValueError("proposal differs from authorized scope/date/catalog")
            call = replace(
                call,
                status=proposal.status,
                item=proposal.item,
                reason=proposal.reason,
                elapsed_seconds=time.monotonic() - began,
            )
        except ModelFailure as error:
            call = replace(
                call, status="failed", reason=error.reason, elapsed_seconds=time.monotonic() - began
            )
        except (ValueError, TypeError):
            call = replace(
                call,
                status="failed",
                reason="invalid_model_output",
                elapsed_seconds=time.monotonic() - began,
            )
        # Measured usage is unknown on transport failure, never fabricated as zero.
        call = replace(
            call,
            elapsed_seconds=time.monotonic() - began,
            prompt_tokens=reply.prompt_tokens if reply else None,
            completion_tokens=reply.completion_tokens if reply else None,
        )
        self.store.finish(call)
        return self._route(call, context)

    def _route(self, call: InterpretationCall, context: RequestContext) -> QuestionOutcome:
        if call.status != "investigate" or call.item is None:
            return QuestionOutcome(call, None)
        view = self.composition.runtime.begin(
            call.run_id, WorkflowRequest(call.item, call.as_of), context=context
        )
        return QuestionOutcome(call, view)

    def _call(self, run_id: str, context: RequestContext) -> InterpretationCall:
        context.require(Permission.READ_EVIDENCE)
        self.composition.runs.resume(run_id, context=context)
        call = self.store.get(run_id)
        if call.run_id != run_id:
            raise ModelFailure("interpretation_store_unavailable")
        return call

    def status(self, run_id: str, *, context: RequestContext) -> QuestionOutcome:
        call = self._call(run_id, context)
        view = (
            self.composition.runtime.status(run_id, context=context)
            if call.status == "investigate"
            else None
        )
        return QuestionOutcome(call, view)

    def recover(self, run_id: str, *, context: RequestContext) -> QuestionOutcome:
        call = self._call(run_id, context)
        # Pending means interrupted/unknown: never replay inference automatically.
        return self._route(call, context)
