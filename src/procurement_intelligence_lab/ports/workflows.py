"""Replaceable execution runtime. State/checkpoint IDs are deliberately absent."""

from typing import Protocol

from procurement_intelligence_lab.platform.semantics.scope import RequestContext
from procurement_intelligence_lab.platform.semantics.workflows import WorkflowRequest, WorkflowView


class AgentWorkflowRuntime(Protocol):
    def start(self, request: WorkflowRequest, *, context: RequestContext) -> WorkflowView: ...
    def status(self, run_id: str, *, context: RequestContext) -> WorkflowView: ...
    def recover(self, run_id: str, *, context: RequestContext) -> WorkflowView: ...
    def review(
        self, run_id: str, brief_id: str, digest: str, decision: str, *, context: RequestContext
    ) -> WorkflowView: ...
