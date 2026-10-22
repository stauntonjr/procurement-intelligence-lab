"""Explicit local execution service and JSON projection of retained typed results."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from procurement_intelligence_lab.application.asserted_document_stages import AssertedDocumentResult
from procurement_intelligence_lab.application.document_stages import DocumentStageResult
from procurement_intelligence_lab.application.normalized_document_stages import (
    NormalizedDocumentResult,
)
from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix, prepare_prefix
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    PrefixExecutionReceipt,
    plan_payload,
)
from procurement_intelligence_lab.platform.execution.executors import ExecutorRegistry
from procurement_intelligence_lab.platform.execution.identity import encoded
from procurement_intelligence_lab.platform.execution.runner import PrefixExecution, run_prefix
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationRegistry,
)
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError


@dataclass(frozen=True)
class PlannedBomExecution:
    execution: PrefixExecution

    def as_dict(self) -> dict[str, Any]:
        a = self.execution.output
        n = a.previous
        m = n.previous
        s = m.previous
        c = s.previous
        documents = DocumentStageResult(
            c.artifact, s.document, m.document, (c.event, s.event, m.event)
        )
        normalized = NormalizedDocumentResult(
            documents, n.observations, n.provenance, n.policy_reference
        )
        asserted = AssertedDocumentResult(
            normalized, a.assertions, a.mentions, a.origin, a.provenance
        )
        r = self.execution.receipt
        return {
            **asserted.as_dict(),
            "execution_receipt": execution_receipt_payload(r),
        }


def execution_receipt_payload(r: PrefixExecutionReceipt) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "stop_after": "ASSERT",
        "requested_prefix_complete": r.requested_prefix_complete,
        "package_execution_complete": r.package_execution_complete,
        "execution_digest": r.execution_digest,
        "receipt_digest": r.receipt_digest,
        "plan_hash": r.plan.plan_hash,
        "plan": plan_payload(r.plan),
        "context": encoded(r.context),
        "source_reference_id": r.source.reference_id,
        "resolved_references": encoded(r.references),
        "entries": encoded(r.entries),
        "completed_at": r.completed_at.isoformat(),
        "execution_context_basis": "caller_pinned_local_manifest",
        "durable_run_journal_updated": False,
        "result_cache_updated": False,
    }


@dataclass(frozen=True)
class PlannedBomExecutionService:
    manifest: bytes
    registry: ImplementationRegistry
    config: ImplementationConfig
    executor_factory: Callable[[datetime], ExecutorRegistry]
    clock: Callable[[], datetime]

    def prepare(self, request: ExecutionRequest) -> PreparedPrefix:
        if type(request) is not ExecutionRequest:
            raise PackageExecutionError("planned execution requires a typed request")
        return prepare_prefix(
            self.manifest,
            registry=self.registry,
            config=self.config,
            executors=self.executor_factory(request.captured_at),
            request=request,
            now=self.clock(),
        )

    def execute(self, request: ExecutionRequest) -> PlannedBomExecution:
        return PlannedBomExecution(run_prefix(self.prepare(request), clock=self.clock))
