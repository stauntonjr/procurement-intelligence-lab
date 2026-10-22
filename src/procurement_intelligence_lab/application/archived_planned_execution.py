"""Explicit execution then atomic retention, and source-free verified recovery."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from procurement_intelligence_lab.application.archived_documents import receipt_payload
from procurement_intelligence_lab.application.planned_bom_execution import (
    PlannedBomExecution,
    PlannedBomExecutionService,
    execution_receipt_payload,
)
from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    ExecutionHistoryPage,
    same_computation,
)
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.execution.runner import PrefixExecution, run_prefix
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore
from procurement_intelligence_lab.ports.planned_execution_archive import PlannedExecutionArchive


def execution_archive_receipt_payload(receipt: ExecutionArchiveReceipt) -> dict[str, Any]:
    return {
        "receipt_id": receipt.receipt_id,
        "sequence": receipt.sequence,
        "execution_digest": receipt.execution_digest,
        "retained_receipt_digest": receipt.retained_receipt_digest,
        "scope": vars(receipt.scope),
        "snapshot_id": receipt.snapshot_id,
        "source_receipt": receipt_payload(receipt.source_receipt),
    }


@dataclass(frozen=True)
class ArchivedPlannedBomResult:
    current: PlannedBomExecution
    retained: ArchivedPrefix

    def __post_init__(self) -> None:
        candidate = CompletedPrefixSnapshot.from_execution(
            self.current.execution.receipt,
            self.retained.completed.snapshot.normalization_policy_parameters,
        )
        if not same_computation(candidate, self.retained.completed):
            raise ArchiveContractError("current and retained execution computations disagree")

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.current.as_dict(),
            "archive_receipt": execution_archive_receipt_payload(self.retained.receipt),
            "retained_execution_receipt": execution_receipt_payload(
                self.retained.completed.execution
            ),
        }


@dataclass(frozen=True)
class ArchivedPlannedBomService:
    executions: PlannedBomExecutionService
    content_store: ArtifactContentStore
    archive_factory: Callable[[], PlannedExecutionArchive]
    policy_parameters: tuple[tuple[str, str], ...]
    validate_completed: Callable[[CompletedPrefixSnapshot], None]

    def execute(self, request: ExecutionRequest) -> ArchivedPlannedBomResult:
        prepared = self.executions.prepare(request)
        archive = self.archive_factory()
        archive.check_ready()
        current = PlannedBomExecution(run_prefix(prepared, clock=self.executions.clock))
        try:
            completed = CompletedPrefixSnapshot.from_execution(
                current.execution.receipt, self.policy_parameters
            )
            self.validate_completed(completed)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveContractError(
                "completed planned execution failed archive validation"
            ) from None
        content = self.content_store.get(completed.snapshot.artifact.content_hash)
        retained = archive.append(completed, content)
        return ArchivedPlannedBomResult(current, retained)


@dataclass(frozen=True)
class PlannedExecutionArchiveReader:
    archive: PlannedExecutionArchive
    validate_completed: Callable[[CompletedPrefixSnapshot], None]

    def _load(self, scope: StateScope, execution_digest: str) -> ArchivedPrefix:
        retained = self.archive.load(scope, execution_digest)
        try:
            self.validate_completed(retained.completed)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveIntegrityError(
                "retained completed planned execution failed validation"
            ) from None
        return retained

    def show(self, scope: StateScope, execution_digest: str) -> ArchivedPlannedBomResult:
        retained = self._load(scope, execution_digest)
        r = retained.completed.execution
        return ArchivedPlannedBomResult(PlannedBomExecution(PrefixExecution(r.output, r)), retained)

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ExecutionHistoryPage:
        page = self.archive.history(scope, limit=limit, after_sequence=after_sequence)
        for receipt in page.receipts:
            self._load(scope, receipt.execution_digest)
        return page

    def content(self, scope: StateScope, execution_digest: str) -> bytes:
        self._load(scope, execution_digest)
        return self.archive.content(scope, execution_digest)
