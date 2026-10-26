"""Explicit claim/run/publication; acknowledgement uncertainty is not execution failure."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.execution.identity import same
from procurement_intelligence_lab.platform.execution.outputs import CapturedOutput
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.execution.resolution_runner import run_resolved_prefix
from procurement_intelligence_lab.platform.processing.resolved_binding import validate_completion
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobFailure,
    JobStatus,
    PinnedResolvedPrefixDefinition,
    ResolvedAbandonAttemptCommand,
    ResolvedAttemptToken,
    ResolvedJobDefinition,
    ResolvedJobJournalReceipt,
    ResolvedStartAttemptCommand,
    ResolvedStartClaim,
    TransitionKind,
    require,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobBusyError,
    ResolvedJobConflictError,
    ResolvedJobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
    SemanticTypeContractError,
)
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore
from procurement_intelligence_lab.ports.resolved_prefix_jobs import ResolvedPrefixJobs


class ResolvedAttemptAcknowledgementUnavailable(ResolvedJobUnavailableError):
    """An unavailable operation after this exact attempt was acknowledged."""

    def __init__(self, token: ResolvedAttemptToken, message: str | None = None) -> None:
        self.token = token
        super().__init__(
            message or "local prefix acknowledgement unavailable; inspect retained job evidence"
        )


class ResolvedRecordedAttemptError(SemanticContractError):
    """Original stable failure classification with only an allowlisted diagnostic."""

    def __init__(self, failure: JobFailure) -> None:
        self.failure = failure
        super().__init__(failure.diagnostic)

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.failure.code.value,
            "category": self.failure.category.value,
            "message": self.failure.diagnostic,
        }


def classify_failure(exc: Exception) -> JobFailure:
    if isinstance(exc, (SemanticContractError, SemanticTypeContractError)):
        category, code = exc.category, exc.code
    else:
        category, code = ErrorCategory.INFRASTRUCTURE, ErrorCode.RESOLVED_PREFIX_JOB_UNAVAILABLE
    diagnostic = {
        ErrorCategory.INPUT: "input_invalid",
        ErrorCategory.INTERPRETATION: "interpretation_failed",
        ErrorCategory.IDENTITY: "input_invalid",
        ErrorCategory.POLICY: "policy_invalid",
        ErrorCategory.INFRASTRUCTURE: "infrastructure_failure",
        ErrorCategory.TRANSIENT: "transient_failure",
        ErrorCategory.AUTHORIZATION: "authorization_denied",
    }[category]
    return JobFailure(code, category, diagnostic)


@dataclass(frozen=True)
class ResolvedJobExecutionResult:
    receipt: ResolvedJobJournalReceipt
    command_receipt: ResolvedJobJournalReceipt
    historical: bool
    observed_version: int


@dataclass(frozen=True)
class ResolvedPrefixJobService:
    journal_factory: Callable[[], ResolvedPrefixJobs]
    prepare_stored: Callable[[PinnedResolvedPrefixDefinition], PreparedResolvedPrefix]
    content_store: ArtifactContentStore
    validate_completed: Callable[[CompletedResolvedPrefixSnapshot], None]
    clock: Callable[[], datetime]

    def submit(self, job: ResolvedJobDefinition) -> ResolvedJobJournalReceipt:
        prepared = self.prepare_stored(job.definition)
        expected = PinnedResolvedPrefixDefinition.from_prepared(
            prepared,
            recipe_id=job.definition.recipe_id,
            normalization_parameters=job.definition.prefix.normalization_parameters,
        )
        require(same(expected, job.definition))
        journal = self.journal_factory()
        journal.check_ready()
        return journal.submit(job, now=self.clock())

    def _historical_outcome(
        self, journal: ResolvedPrefixJobs, claim: ResolvedStartClaim
    ) -> ResolvedJobJournalReceipt:
        cursor = 0
        while True:
            page = journal.history(claim.token.scope, claim.token.job_id, after_sequence=cursor)
            for receipt in page.receipts:
                t = receipt.transition
                if same(t.attempt, claim.token) and t.kind is not TransitionKind.STARTED:
                    if t.status is JobStatus.SUCCEEDED:
                        assert t.success is not None
                        self.validate_completed(t.success.completed)
                        return receipt
                    if t.failure is not None:
                        raise ResolvedRecordedAttemptError(t.failure)
                    raise ResolvedJobConflictError(
                        "historical attempt was abandoned; a new explicit retry is required"
                    )
            if not page.has_more:
                raise ResolvedJobBusyError("historical attempt remains unresolved")
            assert page.next_after_sequence is not None
            cursor = page.next_after_sequence

    def _replay(
        self, journal: ResolvedPrefixJobs, claim: ResolvedStartClaim
    ) -> ResolvedJobExecutionResult:
        try:
            outcome = self._historical_outcome(journal, claim)
            return ResolvedJobExecutionResult(
                outcome,
                claim.receipt,
                True,
                journal.load(claim.token.scope, claim.token.job_id).version,
            )
        except ResolvedJobUnavailableError:
            raise ResolvedAttemptAcknowledgementUnavailable(claim.token) from None

    def execute(self, command: ResolvedStartAttemptCommand) -> ResolvedJobExecutionResult:
        journal = self.journal_factory()
        journal.check_ready()
        # Exact historical replay must not depend on current deployment support.
        if journal.lookup_command(command) is not None:
            claim = journal.start(command, now=self.clock())
            return self._replay(journal, claim)
        view = journal.load(command.scope, command.job_id)
        prepared = self.prepare_stored(view.definition.definition)
        claim = journal.start(command, now=self.clock())
        if not claim.newly_claimed:
            return self._replay(journal, claim)
        job = view.definition

        def guard(captured: CapturedOutput) -> None:
            require(
                captured.artifact.content_hash == job.arrival.expected_content_hash
                and captured.artifact.byte_length == job.arrival.expected_byte_length
            )

        try:
            current = run_resolved_prefix(prepared, clock=self.clock, capture_guard=guard)
            completed = CompletedResolvedPrefixSnapshot.from_execution(
                current.receipt, job.definition.prefix.normalization_parameters
            )
            self.validate_completed(completed)
            content = self.content_store.get(completed.prefix.snapshot.artifact.content_hash)
            validate_completion(job, completed, content)
        except Exception as exc:  # noqa: BLE001 - persist only a finite safe diagnostic before publication.
            failure = classify_failure(exc)
            try:
                journal.fail(claim.token, failure, now=self.clock())
            except ResolvedJobUnavailableError:
                raise ResolvedAttemptAcknowledgementUnavailable(claim.token) from None
            if isinstance(exc, (SemanticContractError, SemanticTypeContractError)):
                raise ResolvedRecordedAttemptError(failure) from None
            raise ResolvedAttemptAcknowledgementUnavailable(
                claim.token, "local prefix execution failed safely; inspect retained job evidence"
            ) from None
        # Do not extend the failure catch across publication: commit may be acknowledged late.
        try:
            outcome = journal.complete(claim.token, completed, content, now=self.clock())
        except ResolvedJobUnavailableError:
            raise ResolvedAttemptAcknowledgementUnavailable(claim.token) from None
        return ResolvedJobExecutionResult(outcome, claim.receipt, False, outcome.transition.version)

    def abandon(self, command: ResolvedAbandonAttemptCommand) -> ResolvedJobJournalReceipt:
        return self.journal_factory().abandon(command, now=self.clock())
