"""Immutable six-stage retention bindings; first-retained prefix stays separate."""

from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    execution_key,
    history_bounds,
    require,
    same_computation,
)
from procurement_intelligence_lab.platform.execution.identity import canonical, digest
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedPrefixExecutionReceipt,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class CompletedResolvedPrefixSnapshot:
    execution: ResolvedPrefixExecutionReceipt
    prefix: CompletedPrefixSnapshot

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.execution) is ResolvedPrefixExecutionReceipt
            and type(self.prefix) is CompletedPrefixSnapshot
        )
        require(canonical(self.execution.prefix) == canonical(self.prefix.execution))

    @classmethod
    def from_execution(
        cls,
        execution: ResolvedPrefixExecutionReceipt,
        policy_parameters: tuple[tuple[str, str], ...],
    ) -> "CompletedResolvedPrefixSnapshot":
        require(type(execution) is ResolvedPrefixExecutionReceipt)
        return cls(
            execution, CompletedPrefixSnapshot.from_execution(execution.prefix, policy_parameters)
        )

    @property
    def scope(self) -> StateScope:
        return self.prefix.scope

    @property
    def execution_digest(self) -> str:
        return self.execution.execution_digest


def same_resolved_computation(
    left: CompletedResolvedPrefixSnapshot, right: CompletedResolvedPrefixSnapshot
) -> bool:
    return (
        left.execution.computation_payload == right.execution.computation_payload
        and same_computation(left.prefix, right.prefix)
    )


@dataclass(frozen=True)
class ResolvedExecutionArchiveReceipt:
    sequence: int
    execution_digest: str
    retained_receipt_digest: str
    prefix_receipt: ExecutionArchiveReceipt

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.sequence) is int
            and self.sequence > 0
            and type(self.prefix_receipt) is ExecutionArchiveReceipt
        )
        execution_key(self.execution_digest)
        execution_key(self.retained_receipt_digest)

    @property
    def scope(self) -> StateScope:
        return self.prefix_receipt.scope

    @property
    def snapshot_id(self) -> str:
        return self.prefix_receipt.snapshot_id

    @property
    def receipt_id(self) -> str:
        return "resolved-execution-archive-receipt-v1:" + digest(self)


@dataclass(frozen=True)
class ArchivedResolvedPrefix:
    completed: CompletedResolvedPrefixSnapshot
    receipt: ResolvedExecutionArchiveReceipt
    retained_prefix: ArchivedPrefix

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.completed) is CompletedResolvedPrefixSnapshot
            and type(self.receipt) is ResolvedExecutionArchiveReceipt
            and type(self.retained_prefix) is ArchivedPrefix
        )
        require(
            self.receipt.execution_digest == self.completed.execution_digest
            and self.receipt.retained_receipt_digest == self.completed.execution.receipt_digest
            and canonical(self.receipt.prefix_receipt) == canonical(self.retained_prefix.receipt)
            and same_computation(self.completed.prefix, self.retained_prefix.completed)
        )


@dataclass(frozen=True)
class ResolvedExecutionHistoryPage:
    scope: StateScope
    after_sequence: int
    limit: int
    receipts: tuple[ResolvedExecutionArchiveReceipt, ...]
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
                type(r) is ResolvedExecutionArchiveReceipt
                and canonical(r.scope) == canonical(self.scope)
                and r.sequence > previous
            )
            previous = r.sequence
        if self.has_more:
            require(
                bool(self.receipts)
                and len(self.receipts) == self.limit
                and type(self.next_after_sequence) is int
                and self.next_after_sequence == previous
            )
        else:
            require(self.next_after_sequence is None)
