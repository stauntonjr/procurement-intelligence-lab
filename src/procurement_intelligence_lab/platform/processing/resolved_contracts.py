"""Additive six-stage job contracts; original five-stage records stay frozen."""

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from typing import cast

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix
from procurement_intelligence_lab.platform.execution.archive import scope_contract
from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
from procurement_intelligence_lab.platform.execution.identity import (
    aware,
    canonical,
    digest,
    digest_text,
    same,
    text,
)
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
    ResolvedExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateInputEvidence,
    ResolutionPolicyEvidence,
)
from procurement_intelligence_lab.platform.planning.contracts import ImplementationDescriptor
from procurement_intelligence_lab.platform.processing.contracts import (
    ArtifactArrival,
    JobFailure,
    JobStatus,
    PinnedPrefixDefinition,
    StartIntent,
    TransitionKind,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobContractError,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope

MAX_COUNTER = 2**63 - 1


def require(condition: bool) -> None:
    if not condition:
        raise ResolvedJobContractError("local job requires exact immutable scoped evidence")


def integer(value: object, *, minimum: int = 1, maximum: int = MAX_COUNTER) -> None:
    require(type(value) is int and minimum <= value <= maximum)


def key(value: str) -> None:
    text(value)
    require(len(value) <= 256)


def job_key(value: str) -> None:
    require(type(value) is str and value.startswith("local-resolved-prefix-job-v1:"))
    digest_text(value.removeprefix("local-resolved-prefix-job-v1:"))


def validate_graph(value: object) -> None:
    try:
        immutable_output(value)
        require(len(canonical(value)) <= 16 * 1024 * 1024)
        seen: set[int] = set()
        active: set[int] = set()

        def visit(item: object, depth: int = 0) -> None:
            require(depth <= 64)
            if is_dataclass(item) and not isinstance(item, type):
                identity = id(item)
                require(identity not in active)
                if identity in seen:
                    return
                seen.add(identity)
                require(len(seen) <= 50000)
                active.add(identity)
                for field in fields(item):
                    visit(getattr(item, field.name), depth + 1)
                active.remove(identity)
            elif isinstance(item, tuple):
                for child in cast(tuple[object, ...], item):
                    visit(child, depth + 1)

        visit(value)
    except (SemanticContractError, TypeError, ValueError, RecursionError):
        raise ResolvedJobContractError(
            "resolved job evidence exceeds its immutable profile"
        ) from None


@dataclass(frozen=True)
class PinnedResolutionMetadata:
    descriptor: ImplementationDescriptor
    settings: tuple[tuple[str, str], ...]
    references: tuple[ResolvedReference, ...]
    policy_version: str

    def __post_init__(self) -> None:
        require(
            type(self.descriptor) is ImplementationDescriptor
            and self.descriptor.stage is StageId.RESOLVE
        )
        require(type(self.settings) is tuple and not self.settings)
        require(
            type(self.references) is tuple
            and all(type(r) is ResolvedReference for r in self.references)
        )
        text(self.policy_version)
        validate_graph(self)


@dataclass(frozen=True)
class PinnedResolvedPrefixDefinition:
    prefix: PinnedPrefixDefinition
    candidate_input: CandidateInputEvidence
    policy: ResolutionPolicyEvidence
    resolution_metadata: PinnedResolutionMetadata
    recipe_id: str

    def __post_init__(self) -> None:
        from procurement_intelligence_lab.platform.processing.resolved_binding import (
            validate_definition,
        )

        validate_definition(self)

    @property
    def request(self):
        return self.prefix.request

    @property
    def resolved_request(self) -> ResolvedExecutionRequest:
        return ResolvedExecutionRequest(
            self.request, self.candidate_input, self.policy, StageId.RESOLVE
        )

    @classmethod
    def from_prepared(
        cls,
        prepared: PreparedResolvedPrefix,
        *,
        recipe_id: str,
        normalization_parameters: tuple[tuple[str, str], ...],
    ) -> "PinnedResolvedPrefixDefinition":
        require(
            type(prepared) is PreparedResolvedPrefix and type(prepared.prefix) is PreparedPrefix
        )
        r = prepared.registration
        return cls(
            PinnedPrefixDefinition.from_prepared(
                prepared.prefix,
                recipe_id=recipe_id,
                normalization_parameters=normalization_parameters,
            ),
            prepared.request.candidate_input,
            prepared.request.policy,
            PinnedResolutionMetadata(r.descriptor, r.settings, r.references, r.policy_version),
            recipe_id,
        )


@dataclass(frozen=True)
class ResolvedJobDefinition:
    arrival: ArtifactArrival
    idempotency_key: str
    definition: PinnedResolvedPrefixDefinition

    def __post_init__(self) -> None:
        require(
            type(self.arrival) is ArtifactArrival
            and type(self.definition) is PinnedResolvedPrefixDefinition
        )
        try:
            key(self.idempotency_key)
        except SemanticContractError:
            raise ResolvedJobContractError("invalid job idempotency key") from None
        require(same(self.arrival.source, self.definition.request.source))
        validate_graph(self)

    @property
    def scope(self) -> StateScope:
        return self.arrival.scope

    @property
    def job_id(self) -> str:
        return "local-resolved-prefix-job-v1:" + digest((self.scope, self.idempotency_key))

    @property
    def request_digest(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ResolvedStartAttemptCommand:
    scope: StateScope
    job_id: str
    command_key: str
    actor: str
    expected_version: int
    intent: StartIntent

    def __post_init__(self) -> None:
        command_contract(
            self.scope, self.job_id, self.command_key, self.actor, self.expected_version
        )
        require(type(self.intent) is StartIntent)

    @property
    def family(self) -> str:
        return "START"


@dataclass(frozen=True)
class ResolvedAbandonAttemptCommand:
    scope: StateScope
    job_id: str
    command_key: str
    actor: str
    expected_version: int
    attempt_id: str
    reason: str

    def __post_init__(self) -> None:
        command_contract(
            self.scope, self.job_id, self.command_key, self.actor, self.expected_version
        )
        text(self.attempt_id)
        text(self.reason)

    @property
    def family(self) -> str:
        return "ABANDON"


def command_contract(
    scope: StateScope, job_id: str, command_key: str, actor: str, version: int
) -> None:
    try:
        scope_contract(scope)
        job_key(job_id)
        key(command_key)
        text(actor)
        integer(version)
    except SemanticContractError:
        raise ResolvedJobContractError("invalid local job command") from None


@dataclass(frozen=True)
class ResolvedAttemptToken:
    scope: StateScope
    job_id: str
    attempt_id: str
    ordinal: int
    fence: int

    def __post_init__(self) -> None:
        scope_contract(self.scope)
        job_key(self.job_id)
        integer(self.ordinal)
        integer(self.fence)
        require(
            self.attempt_id
            == "local-resolved-prefix-attempt-v1:" + digest((self.scope, self.job_id, self.ordinal))
        )


@dataclass(frozen=True)
class ResolvedAttemptSuccess:
    completed: CompletedResolvedPrefixSnapshot
    retained: ResolvedExecutionArchiveReceipt

    def __post_init__(self) -> None:
        require(
            type(self.completed) is CompletedResolvedPrefixSnapshot
            and type(self.retained) is ResolvedExecutionArchiveReceipt
        )
        require(
            self.completed.execution_digest == self.retained.execution_digest
            and self.completed.prefix.snapshot.snapshot_id == self.retained.snapshot_id
            and same(self.completed.scope, self.retained.scope)
        )
        validate_graph(self)


@dataclass(frozen=True)
class ResolvedJobTransition:
    scope: StateScope
    job_id: str
    sequence: int
    version: int
    kind: TransitionKind
    status: JobStatus
    recorded_at: datetime
    command: ResolvedStartAttemptCommand | ResolvedAbandonAttemptCommand | None = None
    attempt: ResolvedAttemptToken | None = None
    failure: JobFailure | None = None
    success: ResolvedAttemptSuccess | None = None

    def __post_init__(self) -> None:
        scope_contract(self.scope)
        job_key(self.job_id)
        integer(self.sequence)
        integer(self.version)
        aware(self.recorded_at)
        require(
            self.version == self.sequence
            and type(self.kind) is TransitionKind
            and type(self.status) is JobStatus
        )
        expected = (
            JobStatus.RUNNING if self.kind is TransitionKind.STARTED else JobStatus(self.kind.value)
        )
        require(self.status is expected)
        require((self.kind is TransitionKind.SUBMITTED) == (self.attempt is None))
        require((self.kind is TransitionKind.SUBMITTED) == (self.version == 1))
        require((self.kind is TransitionKind.FAILED) == (self.failure is not None))
        require((self.kind is TransitionKind.SUCCEEDED) == (self.success is not None))
        require(
            (self.kind in (TransitionKind.STARTED, TransitionKind.ABANDONED))
            == (self.command is not None)
        )
        if self.command is not None:
            require(
                type(self.command)
                is (
                    ResolvedStartAttemptCommand
                    if self.kind is TransitionKind.STARTED
                    else ResolvedAbandonAttemptCommand
                )
            )
            require(
                self.command.expected_version == self.version - 1
                and same(self.command.scope, self.scope)
                and self.command.job_id == self.job_id
            )
        if self.attempt is not None:
            require(
                type(self.attempt) is ResolvedAttemptToken
                and same(self.attempt.scope, self.scope)
                and self.attempt.job_id == self.job_id
            )
            if type(self.command) is ResolvedAbandonAttemptCommand:
                require(self.command.attempt_id == self.attempt.attempt_id)
        if self.failure is not None:
            require(type(self.failure) is JobFailure)
        if self.success is not None:
            require(
                type(self.success) is ResolvedAttemptSuccess
                and same(self.success.completed.scope, self.scope)
            )
        validate_graph(self)

    @property
    def record_id(self) -> str:
        return "local-resolved-prefix-transition-v1:" + digest(self)


@dataclass(frozen=True)
class ResolvedJobJournalReceipt:
    transition: ResolvedJobTransition

    def __post_init__(self) -> None:
        require(type(self.transition) is ResolvedJobTransition)


@dataclass(frozen=True)
class ResolvedStartClaim:
    receipt: ResolvedJobJournalReceipt
    token: ResolvedAttemptToken
    newly_claimed: bool

    def __post_init__(self) -> None:
        require(
            type(self.receipt) is ResolvedJobJournalReceipt and type(self.newly_claimed) is bool
        )
        require(
            self.receipt.transition.kind is TransitionKind.STARTED
            and same(self.token, self.receipt.transition.attempt)
        )


@dataclass(frozen=True)
class ResolvedJobView:
    definition: ResolvedJobDefinition
    latest: ResolvedJobJournalReceipt

    def __post_init__(self) -> None:
        require(
            type(self.definition) is ResolvedJobDefinition
            and type(self.latest) is ResolvedJobJournalReceipt
        )
        require(
            self.definition.job_id == self.latest.transition.job_id
            and same(self.definition.scope, self.latest.transition.scope)
        )
        require(self.definition.arrival.announced_at <= self.latest.transition.recorded_at)

    @property
    def status(self) -> JobStatus:
        return self.latest.transition.status

    @property
    def version(self) -> int:
        return self.latest.transition.version


@dataclass(frozen=True)
class ResolvedJobHistoryPage:
    scope: StateScope
    job_id: str
    after_sequence: int
    limit: int
    receipts: tuple[ResolvedJobJournalReceipt, ...]
    has_more: bool
    next_after_sequence: int | None

    def __post_init__(self) -> None:
        history_bounds(self.scope, self.job_id, self.limit, self.after_sequence)
        require(
            type(self.receipts) is tuple
            and len(self.receipts) <= self.limit
            and type(self.has_more) is bool
        )
        previous = self.after_sequence
        for receipt in self.receipts:
            require(type(receipt) is ResolvedJobJournalReceipt)
            r = receipt.transition
            require(r.job_id == self.job_id and same(r.scope, self.scope) and r.sequence > previous)
            previous = r.sequence
        require(
            (len(self.receipts) == self.limit and self.next_after_sequence == previous)
            if self.has_more
            else self.next_after_sequence is None
        )


def history_bounds(scope: StateScope, job_id: str, limit: int, after_sequence: int) -> None:
    scope_contract(scope)
    job_key(job_id)
    integer(limit, maximum=200)
    integer(after_sequence, minimum=0)
