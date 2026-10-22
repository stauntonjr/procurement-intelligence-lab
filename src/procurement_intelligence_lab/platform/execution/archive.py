"""Exact completed-prefix retention contracts, independent of persistence and domain policy."""

from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.contracts import PrefixExecutionReceipt
from procurement_intelligence_lab.platform.execution.identity import (
    canonical,
    digest,
    digest_text,
    text,
)
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt, DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def require(condition: bool) -> None:
    if not condition:
        raise ArchiveContractError("planned archive requires exact immutable execution evidence")


def scope_contract(scope: StateScope) -> None:
    require(type(scope) is StateScope)
    try:
        for value in vars(scope).values():
            text(value)
    except SemanticContractError:
        require(False)


def history_bounds(scope: StateScope, limit: int, after_sequence: int) -> None:
    scope_contract(scope)
    require(type(limit) is int and 1 <= limit <= 200)
    require(type(after_sequence) is int and after_sequence >= 0)


def execution_key(value: str) -> None:
    try:
        digest_text(value)
    except SemanticContractError:
        require(False)


def _snapshot(
    execution: PrefixExecutionReceipt, parameters: tuple[tuple[str, str], ...]
) -> DocumentSnapshot:
    require(type(execution) is PrefixExecutionReceipt)
    a = execution.output
    n = a.previous
    m = n.previous
    s = m.previous
    return DocumentSnapshot(
        s.document,
        m.document,
        n.observations,
        a.assertions,
        a.mentions,
        tuple(x.event for x in a.chain),
        a.origin,
        n.policy_reference,
        parameters,
    )


@dataclass(frozen=True)
class CompletedPrefixSnapshot:
    execution: PrefixExecutionReceipt
    snapshot: DocumentSnapshot

    def __post_init__(self) -> None:
        try:
            immutable_output(self)
            require(
                type(self.execution) is PrefixExecutionReceipt
                and type(self.snapshot) is DocumentSnapshot
            )
            parameters = self.snapshot.normalization_policy_parameters
            require(type(parameters) is tuple)
            for pair in parameters:
                require(type(pair) is tuple and len(pair) == 2)
                for value in pair:
                    text(value)
            require(
                tuple(sorted(parameters)) == parameters and len(dict(parameters)) == len(parameters)
            )
            require(canonical(self.snapshot) == canonical(_snapshot(self.execution, parameters)))
        except SemanticContractError:
            raise ArchiveContractError(
                "completed prefix and source snapshot must agree exactly"
            ) from None

    @classmethod
    def from_execution(
        cls, execution: PrefixExecutionReceipt, policy_parameters: tuple[tuple[str, str], ...]
    ) -> "CompletedPrefixSnapshot":
        return cls(execution, _snapshot(execution, policy_parameters))

    @property
    def scope(self) -> StateScope:
        return self.execution.source.scope

    @property
    def execution_digest(self) -> str:
        return self.execution.execution_digest


def same_computation(left: CompletedPrefixSnapshot, right: CompletedPrefixSnapshot) -> bool:
    return left.execution.computation_payload == right.execution.computation_payload and canonical(
        left.snapshot
    ) == canonical(right.snapshot)


@dataclass(frozen=True)
class ExecutionArchiveReceipt:
    sequence: int
    execution_digest: str
    retained_receipt_digest: str
    source_receipt: ArchiveReceipt

    def __post_init__(self) -> None:
        require(type(self.sequence) is int and self.sequence > 0)
        execution_key(self.execution_digest)
        execution_key(self.retained_receipt_digest)
        require(type(self.source_receipt) is ArchiveReceipt)
        scope_contract(self.scope)
        try:
            immutable_output(self)
        except SemanticContractError:
            require(False)

    @property
    def scope(self) -> StateScope:
        return self.source_receipt.scope

    @property
    def snapshot_id(self) -> str:
        return self.source_receipt.snapshot_id

    @property
    def receipt_id(self) -> str:
        return "execution-archive-receipt-v1:" + digest(self)


@dataclass(frozen=True)
class ArchivedPrefix:
    completed: CompletedPrefixSnapshot
    receipt: ExecutionArchiveReceipt

    def __post_init__(self) -> None:
        require(
            type(self.completed) is CompletedPrefixSnapshot
            and type(self.receipt) is ExecutionArchiveReceipt
        )
        c = self.completed
        s = c.snapshot
        r = self.receipt
        require(
            r.execution_digest == c.execution_digest
            and r.retained_receipt_digest == c.execution.receipt_digest
        )
        expected = ArchiveReceipt(
            r.source_receipt.sequence,
            s.snapshot_id,
            c.scope,
            s.artifact.artifact_id,
            s.artifact.content_hash,
            len(s.assertions),
            s.origin.recorded_at,
        )
        require(canonical(expected) == canonical(r.source_receipt))


@dataclass(frozen=True)
class ExecutionHistoryPage:
    scope: StateScope
    after_sequence: int
    limit: int
    receipts: tuple[ExecutionArchiveReceipt, ...]
    has_more: bool
    next_after_sequence: int | None

    def __post_init__(self) -> None:
        history_bounds(self.scope, self.limit, self.after_sequence)
        require(type(self.receipts) is tuple and len(self.receipts) <= self.limit)
        previous = self.after_sequence
        for receipt in self.receipts:
            require(type(receipt) is ExecutionArchiveReceipt)
            require(
                canonical(receipt.scope) == canonical(self.scope) and receipt.sequence > previous
            )
            previous = receipt.sequence
        require(type(self.has_more) is bool)
        if self.has_more:
            require(bool(self.receipts) and len(self.receipts) == self.limit)
            require(type(self.next_after_sequence) is int and self.next_after_sequence == previous)
        else:
            require(self.next_after_sequence is None)
