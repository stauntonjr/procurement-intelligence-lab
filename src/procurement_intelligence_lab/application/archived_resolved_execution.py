"""Explicit six-stage publication and pure, validated historical recovery."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from procurement_intelligence_lab.application.archived_planned_execution import (
    execution_archive_receipt_payload,
)
from procurement_intelligence_lab.application.planned_bom_execution import execution_receipt_payload
from procurement_intelligence_lab.application.planned_resolved_bom_execution import (
    PlannedResolvedBomExecution,
    PlannedResolvedBomExecutionService,
    resolved_execution_receipt_payload,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
    CompletedResolvedPrefixSnapshot,
    ResolvedExecutionHistoryPage,
    same_resolved_computation,
)
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
)
from procurement_intelligence_lab.platform.execution.resolution_runner import (
    ResolvedPrefixExecution,
    run_resolved_prefix,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore
from procurement_intelligence_lab.ports.resolved_execution_archive import ResolvedExecutionArchive


@dataclass(frozen=True)
class ArchivedResolvedBomResult:
    current: PlannedResolvedBomExecution
    retained: ArchivedResolvedPrefix

    def __post_init__(self) -> None:
        completed = CompletedResolvedPrefixSnapshot.from_execution(
            self.current.execution.receipt,
            self.retained.completed.prefix.snapshot.normalization_policy_parameters,
        )
        if not same_resolved_computation(completed, self.retained.completed):
            raise ArchiveContractError("current and retained resolved computations disagree")

    def as_dict(self) -> dict[str, Any]:
        r = self.retained.receipt
        return {
            **self.current.as_dict(),
            "archive_receipt": {
                "receipt_id": r.receipt_id,
                "sequence": r.sequence,
                "execution_digest": r.execution_digest,
                "retained_receipt_digest": r.retained_receipt_digest,
                "scope": vars(r.scope),
                "snapshot_id": r.snapshot_id,
                "prefix_receipt": execution_archive_receipt_payload(r.prefix_receipt),
            },
            "retained_execution_receipt": resolved_execution_receipt_payload(
                self.retained.completed.execution
            ),
            "retained_embedded_prefix_execution_receipt": execution_receipt_payload(
                self.retained.completed.execution.prefix
            ),
            "retained_prefix_execution_receipt": execution_receipt_payload(
                self.retained.retained_prefix.completed.execution
            ),
        }


@dataclass(frozen=True)
class ArchivedResolvedBomService:
    executions: PlannedResolvedBomExecutionService
    content_store: ArtifactContentStore
    archive_factory: Callable[[], ResolvedExecutionArchive]
    policy_parameters: tuple[tuple[str, str], ...]
    validate_completed: Callable[[CompletedResolvedPrefixSnapshot], None]

    def execute(self, request: ResolvedExecutionRequest) -> ArchivedResolvedBomResult:
        prepared = self.executions.prepare(request)
        archive = self.archive_factory()
        archive.check_ready()
        current = PlannedResolvedBomExecution(
            run_resolved_prefix(prepared, clock=self.executions.clock)
        )
        try:
            completed = CompletedResolvedPrefixSnapshot.from_execution(
                current.execution.receipt, self.policy_parameters
            )
            self.validate_completed(completed)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveContractError(
                "completed resolved execution failed archive validation"
            ) from None
        content = self.content_store.get(completed.prefix.snapshot.artifact.content_hash)
        return ArchivedResolvedBomResult(current, archive.append(completed, content))


@dataclass(frozen=True)
class ResolvedExecutionArchiveReader:
    archive: ResolvedExecutionArchive
    validate_completed: Callable[[CompletedResolvedPrefixSnapshot], None]
    encode_retained: Callable[[ArchivedResolvedPrefix], bytes]

    def _load(self, scope: StateScope, execution_digest: str) -> ArchivedResolvedPrefix:
        retained = self.archive.load(scope, execution_digest)
        try:
            self.validate_completed(retained.completed)
            self.validate_completed(
                CompletedResolvedPrefixSnapshot.from_execution(
                    retained.completed.execution,
                    retained.retained_prefix.completed.snapshot.normalization_policy_parameters,
                )
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveIntegrityError(
                "retained completed resolved execution failed validation"
            ) from None
        return retained

    def show(self, scope: StateScope, execution_digest: str) -> ArchivedResolvedBomResult:
        retained = self._load(scope, execution_digest)
        r = retained.completed.execution
        return ArchivedResolvedBomResult(
            PlannedResolvedBomExecution(ResolvedPrefixExecution(r.output, r)), retained
        )

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ResolvedExecutionHistoryPage:
        page = self.archive.history(scope, limit=limit, after_sequence=after_sequence)
        for r in page.receipts:
            self._load(scope, r.execution_digest)
        return page

    def content(self, scope: StateScope, execution_digest: str) -> bytes:
        self._load(scope, execution_digest)
        return self.archive.content(scope, execution_digest)

    def export(self, scope: StateScope, execution_digest: str) -> bytes:
        return self.encode_retained(self._load(scope, execution_digest))
