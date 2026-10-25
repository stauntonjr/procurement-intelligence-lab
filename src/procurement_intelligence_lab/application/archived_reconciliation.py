"""Separate current/historical/first-retained projections and verified historical reads."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from procurement_intelligence_lab.application.planned_resolved_bom_execution import (
    PlannedResolvedBomExecution,
)
from procurement_intelligence_lab.application.retained_reconciliation import (
    RetainedReconciliationService,
)
from procurement_intelligence_lab.platform.execution.identity import encoded, same
from procurement_intelligence_lab.platform.execution.outputs import require
from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    ArchivedReconciliation,
    CompletedReconciliationSnapshot,
    ReconciliationArchiveReceipt,
    ReconciliationHistoryPage,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconciliationOperationReceipt,
    same_reconciliation_computation,
)
from procurement_intelligence_lab.platform.execution.resolution_runner import (
    ResolvedPrefixExecution,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
    PackageExecutionContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.reconciliation_archive import ReconciliationArchive


def receipt_payload(r: ReconciliationOperationReceipt) -> dict[str, Any]:
    o = r.output
    return {
        "profile": "retained-resolution-reconciliation/v1",
        "execution_digest": r.execution_digest,
        "receipt_digest": r.receipt_digest,
        "plan_hash": r.plan.plan_hash,
        "plan": json.loads(r.plan.canonical_json),
        "context": encoded(r.context),
        "scope": encoded(o.inputs.scope),
        "as_of": o.inputs.as_of.isoformat(),
        "completed_at": r.completed_at.isoformat(),
        "requested_operation_complete": True,
        "package_execution_complete": False,
        "entries": encoded(r.entries),
        "event": {"event_id": o.event.event_id, **cast(dict[str, Any], encoded(o.event))},
        "batch_id": o.batch_id,
        "policy": encoded(o.inputs.policy),
        "authority": {
            "schema": o.inputs.authority.schema_id,
            "raw_sha256": o.inputs.authority.raw_sha256,
            "semantic_digest": o.inputs.authority.semantic_digest,
            "raw_json_hex": o.inputs.authority.raw_json.hex(),
            "semantic": json.loads(o.inputs.authority.semantic_json),
        },
        "decisions": [
            {"reconciliation_id": d.reconciliation_id, **cast(dict[str, Any], encoded(d))}
            for d in o.decisions
        ],
        "states": [{"state_id": s.state_id, **cast(dict[str, Any], encoded(s))} for s in o.states],
        "outside_predicate_ids": list(o.outside_predicate_ids),
        "domain_audit": json.loads(o.domain_audit),
        "durable_run_journal_updated": False,
        "result_cache_updated": False,
    }


def archive_receipt_payload(r: ReconciliationArchiveReceipt) -> dict[str, Any]:
    return {"receipt_id": r.receipt_id, **cast(dict[str, Any], encoded(r))}


@dataclass(frozen=True)
class RetainedReconciliationResult:
    current_operation: ReconciliationOperationReceipt
    retained: ArchivedReconciliation | None

    def __post_init__(self) -> None:
        require(type(self.current_operation) is ReconciliationOperationReceipt)
        if self.retained is not None:
            require(
                type(self.retained) is ArchivedReconciliation
                and same_reconciliation_computation(
                    self.current_operation, self.retained.completed.execution
                )
            )

    def as_dict(self) -> dict[str, Any]:
        ps = self.current_operation.output.inputs.recorded_producers
        result = {
            "profile": "retained-resolution-reconciliation/v1",
            "recorded_producers": [
                {
                    "archive_receipt": {
                        "receipt_id": p.receipt.receipt_id,
                        **cast(dict[str, Any], encoded(p.receipt)),
                    },
                    **PlannedResolvedBomExecution(
                        ResolvedPrefixExecution(p.completed.execution.output, p.completed.execution)
                    ).as_dict(),
                }
                for p in ps
            ],
            "current_operation": receipt_payload(self.current_operation),
        }
        if self.retained is not None:
            result["archive_receipt"] = archive_receipt_payload(self.retained.receipt)
            result["first_retained_operation"] = receipt_payload(self.retained.completed.execution)
        return result


@dataclass(frozen=True)
class ArchivedReconciliationService:
    executions: RetainedReconciliationService
    archive_factory: Callable[[], ReconciliationArchive]
    validate_completed: Callable[[CompletedReconciliationSnapshot], None]

    def execute(
        self,
        *,
        scope: StateScope,
        as_of: datetime,
        context: ProvenanceContext,
        producer_digests: tuple[str, ...],
    ) -> RetainedReconciliationResult:
        self.executions.preflight(
            scope=scope, as_of=as_of, context=context, producer_digests=producer_digests
        )
        archive = self.archive_factory()
        archive.check_ready()
        current = self.executions.execute(
            scope=scope, as_of=as_of, context=context, producer_digests=producer_digests
        )
        completed = CompletedReconciliationSnapshot(current)
        try:
            self.validate_completed(completed)
            retained = archive.append(completed)
        except ArchiveContractError:
            raise PackageExecutionContractError(
                "reconciliation result exceeds its retained evidence contract"
            ) from None
        return RetainedReconciliationResult(current, retained)


@dataclass(frozen=True)
class ReconciliationArchiveReader:
    archive: ReconciliationArchive
    validate_completed: Callable[[CompletedReconciliationSnapshot], None]
    encode_retained: Callable[[ArchivedReconciliation], bytes]

    def _load(self, scope: StateScope, execution_digest: str) -> ArchivedReconciliation:
        retained = self.archive.load(scope, execution_digest)
        try:
            require(
                same(retained.completed.scope, scope)
                and retained.completed.execution_digest == execution_digest
            )
            self.validate_completed(retained.completed)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveIntegrityError(
                "retained reconciliation failed source and governing-policy validation"
            ) from None
        return retained

    def show(self, scope: StateScope, execution_digest: str) -> RetainedReconciliationResult:
        retained = self._load(scope, execution_digest)
        return RetainedReconciliationResult(retained.completed.execution, retained)

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ReconciliationHistoryPage:
        page = self.archive.history(scope, limit=limit, after_sequence=after_sequence)
        for r in page.receipts:
            self._load(scope, r.execution_digest)
        return page

    def content_manifest(self, scope: StateScope, execution_digest: str) -> dict[str, object]:
        retained = self._load(scope, execution_digest)
        producers: list[dict[str, object]] = []
        for p in retained.completed.execution.output.inputs.recorded_producers:
            a = p.completed.prefix.snapshot.artifact
            d = p.completed.execution_digest
            base = [
                "python",
                "-m",
                "procurement_intelligence_lab.interfaces.resolved_execution_archive",
            ]
            producers.append(
                {
                    "execution_digest": d,
                    "artifact_id": a.artifact_id,
                    "content_hash": a.content_hash,
                    "byte_length": a.byte_length,
                    "commands": {
                        cmd: [
                            *base,
                            cmd,
                            "--scope",
                            "<scope.json>",
                            "--execution-digest",
                            d,
                            *(
                                ["--output", f"<{d}.{'xlsx' if cmd == 'content' else 'json'}>"]
                                if cmd != "show"
                                else []
                            ),
                        ]
                        for cmd in ("show", "content", "export")
                    },
                }
            )
        return {
            "schema": "reconciliation-content-manifest/v1",
            "scope": vars(scope),
            "execution_digest": execution_digest,
            "original_source_bytes_included": False,
            "producers": producers,
        }

    def export(self, scope: StateScope, execution_digest: str) -> bytes:
        retained = self._load(scope, execution_digest)
        try:
            return self.encode_retained(retained)
        except (ValueError, TypeError):
            raise ArchiveIntegrityError(
                "retained reconciliation export exceeds supported bounds"
            ) from None
