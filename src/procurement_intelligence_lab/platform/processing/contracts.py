"""Immutable request, command and transition evidence; no execution authority by inference."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix
from procurement_intelligence_lab.platform.execution.archive import (
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    scope_contract,
)
from procurement_intelligence_lab.platform.execution.contracts import (
    PREFIX,
    ExecutionRequest,
    ResolvedReference,
)
from procurement_intelligence_lab.platform.execution.identity import (
    aware,
    canonical,
    digest,
    digest_text,
    same,
    text,
)
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationRegistry,
    PhysicalPlan,
)
from procurement_intelligence_lab.platform.processing.errors import JobContractError
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope

MAX_COUNTER = 2**63 - 1


def require(condition: bool) -> None:
    if not condition:
        raise JobContractError("local job requires exact immutable scoped evidence")


def integer(value: object, *, minimum: int = 1, maximum: int = MAX_COUNTER) -> None:
    require(type(value) is int and minimum <= value <= maximum)


def key(value: str) -> None:
    text(value)
    require(len(value) <= 256)


def job_key(value: str) -> None:
    require(type(value) is str and value.startswith("local-prefix-job-v1:"))
    digest_text(value.removeprefix("local-prefix-job-v1:"))


def validate_graph(value: object) -> None:
    try:
        immutable_output(value)
        require(len(canonical(value)) <= 16 * 1024 * 1024)
    except (SemanticContractError, TypeError, ValueError, RecursionError):
        raise JobContractError("local job evidence exceeds its immutable profile") from None


class JobStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class AttemptStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class StartIntent(StrEnum):
    FIRST = "FIRST"
    RETRY = "RETRY"


class TransitionKind(StrEnum):
    SUBMITTED = "SUBMITTED"
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True)
class ArtifactArrival:
    scope: StateScope
    event_id: str
    source: SourceReference
    expected_content_hash: str
    expected_byte_length: int
    announced_at: datetime

    def __post_init__(self) -> None:
        require(type(self.source) is SourceReference)
        scope_contract(self.scope)
        require(same(self.scope, self.source.scope))
        try:
            key(self.event_id)
            digest_text(self.expected_content_hash)
            integer(self.expected_byte_length, minimum=0)
            aware(self.announced_at)
            require(self.source.observed_at <= self.announced_at)
        except (SemanticContractError, UnicodeError):
            raise JobContractError("invalid artifact arrival declaration") from None
        validate_graph(self)


@dataclass(frozen=True)
class PinnedStageMetadata:
    stage: StageId
    references: tuple[ResolvedReference, ...]
    policy_version: str | None
    schema_version: str | None

    def __post_init__(self) -> None:
        require(type(self.stage) is StageId and self.stage in PREFIX)
        require(
            type(self.references) is tuple
            and all(type(r) is ResolvedReference for r in self.references)
        )
        require(tuple(sorted(self.references, key=lambda r: r.declaration_ref)) == self.references)
        require(len({r.declaration_ref for r in self.references}) == len(self.references))
        for value in (self.policy_version, self.schema_version):
            if value is not None:
                text(value)
        validate_graph(self)


@dataclass(frozen=True)
class PinnedPrefixDefinition:
    recipe_id: str
    manifest: bytes
    registry: ImplementationRegistry
    config: ImplementationConfig
    request: ExecutionRequest
    normalization_parameters: tuple[tuple[str, str], ...]
    plan: PhysicalPlan
    stage_metadata: tuple[PinnedStageMetadata, ...]

    def __post_init__(self) -> None:
        from procurement_intelligence_lab.platform.processing.binding import validate_definition

        validate_definition(self)

    @classmethod
    def from_prepared(
        cls,
        prepared: PreparedPrefix,
        *,
        recipe_id: str,
        normalization_parameters: tuple[tuple[str, str], ...],
    ) -> "PinnedPrefixDefinition":
        require(type(prepared) is PreparedPrefix)
        return cls(
            recipe_id,
            prepared.manifest,
            prepared.registry,
            prepared.config,
            prepared.request,
            normalization_parameters,
            prepared.plan,
            tuple(
                PinnedStageMetadata(
                    r.descriptor.stage, r.references, r.policy_version, r.schema_version
                )
                for r in prepared.selected
            ),
        )

    @property
    def effective_context(self) -> ProvenanceContext:
        metadata = tuple(
            (r.references, r.policy_version, r.schema_version) for r in self.stage_metadata
        )
        return replace(
            self.request.context, config_digest=digest((self.request.context, self.plan, metadata))
        )


@dataclass(frozen=True)
class JobDefinition:
    arrival: ArtifactArrival
    idempotency_key: str
    definition: PinnedPrefixDefinition

    def __post_init__(self) -> None:
        require(
            type(self.arrival) is ArtifactArrival
            and type(self.definition) is PinnedPrefixDefinition
        )
        try:
            key(self.idempotency_key)
        except SemanticContractError:
            raise JobContractError("invalid job idempotency key") from None
        require(same(self.arrival.source, self.definition.request.source))
        validate_graph(self)

    @property
    def scope(self) -> StateScope:
        return self.arrival.scope

    @property
    def job_id(self) -> str:
        return "local-prefix-job-v1:" + digest((self.scope, self.idempotency_key))

    @property
    def request_digest(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class StartAttemptCommand:
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
class AbandonAttemptCommand:
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
        raise JobContractError("invalid local job command") from None


@dataclass(frozen=True)
class AttemptToken:
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
            == "local-prefix-attempt-v1:" + digest((self.scope, self.job_id, self.ordinal))
        )


# Persisted diagnostics are finite stable labels, never exception messages.
DIAGNOSTICS = frozenset(
    (
        "source_unavailable",
        "content_invalid",
        "execution_invalid",
        "interpretation_failed",
        "policy_invalid",
        "infrastructure_failure",
        "input_invalid",
        "authorization_denied",
        "transient_failure",
    )
)


@dataclass(frozen=True)
class JobFailure:
    code: ErrorCode
    category: ErrorCategory
    diagnostic: str

    def __post_init__(self) -> None:
        require(type(self.code) is ErrorCode and type(self.category) is ErrorCategory)
        require(self.code.value.split(".")[1] == self.category.value)
        require(self.diagnostic in DIAGNOSTICS)


@dataclass(frozen=True)
class AttemptSuccess:
    completed: CompletedPrefixSnapshot
    retained: ExecutionArchiveReceipt

    def __post_init__(self) -> None:
        require(
            type(self.completed) is CompletedPrefixSnapshot
            and type(self.retained) is ExecutionArchiveReceipt
        )
        require(
            self.completed.execution_digest == self.retained.execution_digest
            and self.completed.snapshot.snapshot_id == self.retained.snapshot_id
            and same(self.completed.scope, self.retained.scope)
        )
        validate_graph(self)


@dataclass(frozen=True)
class JobTransition:
    scope: StateScope
    job_id: str
    sequence: int
    version: int
    kind: TransitionKind
    status: JobStatus
    recorded_at: datetime
    command: StartAttemptCommand | AbandonAttemptCommand | None = None
    attempt: AttemptToken | None = None
    failure: JobFailure | None = None
    success: AttemptSuccess | None = None

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
                    StartAttemptCommand
                    if self.kind is TransitionKind.STARTED
                    else AbandonAttemptCommand
                )
            )
            require(
                self.command.expected_version == self.version - 1
                and same(self.command.scope, self.scope)
                and self.command.job_id == self.job_id
            )
        if self.attempt is not None:
            require(
                type(self.attempt) is AttemptToken
                and same(self.attempt.scope, self.scope)
                and self.attempt.job_id == self.job_id
            )
            if type(self.command) is AbandonAttemptCommand:
                require(self.command.attempt_id == self.attempt.attempt_id)
        if self.failure is not None:
            require(type(self.failure) is JobFailure)
        if self.success is not None:
            require(
                type(self.success) is AttemptSuccess
                and same(self.success.completed.scope, self.scope)
            )
        validate_graph(self)

    @property
    def record_id(self) -> str:
        return "local-prefix-transition-v1:" + digest(self)


@dataclass(frozen=True)
class JobJournalReceipt:
    transition: JobTransition

    def __post_init__(self) -> None:
        require(type(self.transition) is JobTransition)


@dataclass(frozen=True)
class StartClaim:
    receipt: JobJournalReceipt
    token: AttemptToken
    newly_claimed: bool

    def __post_init__(self) -> None:
        require(type(self.receipt) is JobJournalReceipt and type(self.newly_claimed) is bool)
        require(
            self.receipt.transition.kind is TransitionKind.STARTED
            and same(self.token, self.receipt.transition.attempt)
        )


@dataclass(frozen=True)
class JobView:
    definition: JobDefinition
    latest: JobJournalReceipt

    def __post_init__(self) -> None:
        require(type(self.definition) is JobDefinition and type(self.latest) is JobJournalReceipt)
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
class JobHistoryPage:
    scope: StateScope
    job_id: str
    after_sequence: int
    limit: int
    receipts: tuple[JobJournalReceipt, ...]
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
            require(type(receipt) is JobJournalReceipt)
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
