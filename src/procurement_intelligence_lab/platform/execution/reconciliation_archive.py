"""Immutable current reconciliation retention with exact historical archive receipts."""

from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.archive import (
    execution_key,
    history_bounds,
    require,
    scope_contract,
)
from procurement_intelligence_lab.platform.execution.identity import canonical, digest
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconciliationOperationReceipt,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ResolvedExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class CompletedReconciliationSnapshot:
    execution: ReconciliationOperationReceipt

    def __post_init__(self) -> None:
        immutable_output(self)
        require(type(self.execution) is ReconciliationOperationReceipt)

    @property
    def scope(self) -> StateScope:
        return self.execution.output.inputs.scope

    @property
    def execution_digest(self) -> str:
        return self.execution.execution_digest


@dataclass(frozen=True)
class ReconciliationArchiveReceipt:
    scope: StateScope
    sequence: int
    execution_digest: str
    retained_receipt_digest: str
    producer_receipts: tuple[ResolvedExecutionArchiveReceipt, ...]

    def __post_init__(self) -> None:
        immutable_output(self)
        scope_contract(self.scope)
        require(type(self.sequence) is int and self.sequence > 0)
        execution_key(self.execution_digest)
        execution_key(self.retained_receipt_digest)
        require(
            type(self.producer_receipts) is tuple
            and 1 <= len(self.producer_receipts) <= 8
            and all(type(p) is ResolvedExecutionArchiveReceipt for p in self.producer_receipts)
        )
        ids = tuple(p.execution_digest for p in self.producer_receipts)
        require(
            ids == tuple(sorted(set(ids)))
            and all(canonical(p.scope) == canonical(self.scope) for p in self.producer_receipts)
        )

    @property
    def receipt_id(self) -> str:
        return "reconciliation-archive-receipt-v1:" + digest(self)


@dataclass(frozen=True)
class ArchivedReconciliation:
    completed: CompletedReconciliationSnapshot
    receipt: ReconciliationArchiveReceipt

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.completed) is CompletedReconciliationSnapshot
            and type(self.receipt) is ReconciliationArchiveReceipt
        )
        require(
            canonical(self.completed.scope) == canonical(self.receipt.scope)
            and self.completed.execution_digest == self.receipt.execution_digest
            and self.completed.execution.receipt_digest == self.receipt.retained_receipt_digest
        )
        require(
            canonical(
                tuple(p.receipt for p in self.completed.execution.output.inputs.recorded_producers)
            )
            == canonical(self.receipt.producer_receipts)
        )


@dataclass(frozen=True)
class ReconciliationHistoryPage:
    scope: StateScope
    after_sequence: int
    limit: int
    receipts: tuple[ReconciliationArchiveReceipt, ...]
    has_more: bool
    next_after_sequence: int | None

    def __post_init__(self) -> None:
        history_bounds(self.scope, self.limit, self.after_sequence)
        require(
            type(self.receipts) is tuple
            and len(self.receipts) <= self.limit
            and type(self.has_more) is bool
        )
        previous = self.after_sequence
        for r in self.receipts:
            require(
                type(r) is ReconciliationArchiveReceipt
                and canonical(r.scope) == canonical(self.scope)
                and r.sequence > previous
            )
            previous = r.sequence
        require(
            type(self.next_after_sequence) is int
            and self.next_after_sequence == previous
            and bool(self.receipts)
            and len(self.receipts) == self.limit
            if self.has_more
            else self.next_after_sequence is None
        )
