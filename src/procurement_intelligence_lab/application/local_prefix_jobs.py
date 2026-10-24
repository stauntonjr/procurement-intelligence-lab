"""Explicit claim/run/publication; acknowledgement uncertainty is not execution failure."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix
from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.execution.identity import same
from procurement_intelligence_lab.platform.execution.outputs import CapturedOutput
from procurement_intelligence_lab.platform.execution.runner import run_prefix
from procurement_intelligence_lab.platform.processing.binding import validate_completion
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    JobDefinition,
    JobFailure,
    JobJournalReceipt,
    JobStatus,
    PinnedPrefixDefinition,
    StartAttemptCommand,
    StartClaim,
    TransitionKind,
    require,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobBusyError,
    JobConflictError,
    JobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
    SemanticTypeContractError,
)
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore
from procurement_intelligence_lab.ports.local_prefix_jobs import LocalPrefixJobs


class RecordedAttemptError(SemanticContractError):
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
        category, code = ErrorCategory.INFRASTRUCTURE, ErrorCode.LOCAL_PREFIX_JOB_UNAVAILABLE
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
class JobExecutionResult:
    receipt: JobJournalReceipt
    command_receipt: JobJournalReceipt
    historical: bool
    observed_version: int


@dataclass(frozen=True)
class LocalPrefixJobService:
    journal_factory: Callable[[], LocalPrefixJobs]
    prepare_stored: Callable[[PinnedPrefixDefinition], PreparedPrefix]
    content_store: ArtifactContentStore
    validate_completed: Callable[[CompletedPrefixSnapshot], None]
    clock: Callable[[], datetime]

    def submit(self, job: JobDefinition) -> JobJournalReceipt:
        prepared = self.prepare_stored(job.definition)
        expected = PinnedPrefixDefinition.from_prepared(
            prepared,
            recipe_id=job.definition.recipe_id,
            normalization_parameters=job.definition.normalization_parameters,
        )
        require(same(expected, job.definition))
        journal = self.journal_factory()
        journal.check_ready()
        return journal.submit(job, now=self.clock())

    def _historical_outcome(self, journal: LocalPrefixJobs, claim: StartClaim) -> JobJournalReceipt:
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
                        raise RecordedAttemptError(t.failure)
                    raise JobConflictError(
                        "historical attempt was abandoned; a new explicit retry is required"
                    )
            if not page.has_more:
                raise JobBusyError("historical attempt remains unresolved")
            assert page.next_after_sequence is not None
            cursor = page.next_after_sequence

    def execute(self, command: StartAttemptCommand) -> JobExecutionResult:
        journal = self.journal_factory()
        journal.check_ready()
        # Exact historical replay must not depend on current deployment support.
        if journal.lookup_command(command) is not None:
            claim = journal.start(command, now=self.clock())
            outcome = self._historical_outcome(journal, claim)
            return JobExecutionResult(
                outcome, claim.receipt, True, journal.load(command.scope, command.job_id).version
            )
        view = journal.load(command.scope, command.job_id)
        prepared = self.prepare_stored(view.definition.definition)
        claim = journal.start(command, now=self.clock())
        if not claim.newly_claimed:
            outcome = self._historical_outcome(journal, claim)
            return JobExecutionResult(
                outcome, claim.receipt, True, journal.load(command.scope, command.job_id).version
            )
        job = view.definition

        def guard(captured: CapturedOutput) -> None:
            require(
                captured.artifact.content_hash == job.arrival.expected_content_hash
                and captured.artifact.byte_length == job.arrival.expected_byte_length
            )

        try:
            current = run_prefix(prepared, clock=self.clock, capture_guard=guard)
            completed = CompletedPrefixSnapshot.from_execution(
                current.receipt, job.definition.normalization_parameters
            )
            self.validate_completed(completed)
            content = self.content_store.get(completed.snapshot.artifact.content_hash)
            validate_completion(job, completed, content)
        except Exception as exc:  # noqa: BLE001 - persist only a finite safe diagnostic before publication.
            failure = classify_failure(exc)
            journal.fail(claim.token, failure, now=self.clock())
            if isinstance(exc, (SemanticContractError, SemanticTypeContractError)):
                raise RecordedAttemptError(failure) from None
            raise JobUnavailableError("local prefix execution failed safely") from None
        # Do not extend the failure catch across publication: commit may be acknowledged late.
        outcome = journal.complete(claim.token, completed, content, now=self.clock())
        return JobExecutionResult(outcome, claim.receipt, False, outcome.transition.version)

    def abandon(self, command: AbandonAttemptCommand) -> JobJournalReceipt:
        return self.journal_factory().abandon(command, now=self.clock())
