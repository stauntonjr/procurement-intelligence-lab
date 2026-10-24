"""Pure transition policy: explicit retry, nonregressing clocks and fences."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    JobFailure,
    JobJournalReceipt,
    JobStatus,
    JobView,
    StartAttemptCommand,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobConflictError,
    JobContractError,
    JobFencedError,
)
from procurement_intelligence_lab.platform.processing.lifecycle import (
    abandon_transition,
    failure_transition,
    start_transition,
    submission_transition,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from tests.local_prefix_job_fixtures import NOW, job_input


def initial(tmp_path: Path) -> JobView:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    return JobView(job, JobJournalReceipt(submission_transition(job, now=NOW)))


def command(
    view: JobView, key: str = "start-1", intent: StartIntent = StartIntent.FIRST
) -> StartAttemptCommand:
    return StartAttemptCommand(
        view.definition.scope, view.definition.job_id, key, "developer", view.version, intent
    )


def test_transition_matrix_and_historical_command_payload(tmp_path: Path) -> None:
    view = initial(tmp_path)
    started = start_transition(view, command(view), now=NOW)
    running = JobView(view.definition, JobJournalReceipt(started))
    assert running.status is JobStatus.RUNNING and running.version == 2
    with pytest.raises(JobConflictError):
        start_transition(running, command(running), now=NOW)
    token = started.attempt
    assert token is not None
    abandoned = abandon_transition(
        running,
        AbandonAttemptCommand(
            view.definition.scope,
            view.definition.job_id,
            "abandon-1",
            "developer",
            2,
            token.attempt_id,
            "lost acknowledgement",
        ),
        now=NOW,
    )
    stopped = JobView(view.definition, JobJournalReceipt(abandoned))
    retry = start_transition(stopped, command(stopped, "retry-1", StartIntent.RETRY), now=NOW)
    assert retry.attempt is not None
    assert retry.attempt.ordinal == 2 and retry.attempt.fence > token.fence
    assert retry.attempt.attempt_id != token.attempt_id
    assert isinstance(retry.command, StartAttemptCommand)
    assert retry.command.intent is StartIntent.RETRY
    assert (
        view.definition.definition.effective_context
        == running.definition.definition.effective_context
    )
    with pytest.raises(JobFencedError):
        failure_transition(
            JobView(view.definition, JobJournalReceipt(retry)),
            token,
            JobFailure(
                ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE,
                ErrorCategory.INFRASTRUCTURE,
                "source_unavailable",
            ),
            now=NOW,
        )


def test_failure_needs_explicit_retry(tmp_path: Path) -> None:
    view = initial(tmp_path)
    running = JobView(
        view.definition, JobJournalReceipt(start_transition(view, command(view), now=NOW))
    )
    assert running.latest.transition.attempt is not None
    failed = failure_transition(
        running,
        running.latest.transition.attempt,
        JobFailure(
            ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE,
            ErrorCategory.INFRASTRUCTURE,
            "source_unavailable",
        ),
        now=NOW,
    )
    failed_view = JobView(view.definition, JobJournalReceipt(failed))
    with pytest.raises(JobConflictError):
        start_transition(failed_view, command(failed_view), now=NOW)
    retried = start_transition(failed_view, command(failed_view, intent=StartIntent.RETRY), now=NOW)
    assert retried.attempt is not None and retried.attempt.ordinal == 2


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, 2**63])
def test_counter_time_and_scope_boundaries(tmp_path: Path, value: object) -> None:
    view = initial(tmp_path)
    with pytest.raises(JobContractError):
        replace(command(view), expected_version=value)


def test_future_arrival_regressing_clock_and_stale_version(tmp_path: Path) -> None:
    view = initial(tmp_path)
    with pytest.raises(JobContractError):
        submission_transition(
            replace(
                view.definition,
                arrival=replace(view.definition.arrival, announced_at=NOW + timedelta(seconds=1)),
            ),
            now=NOW,
        )
    with pytest.raises(JobContractError):
        start_transition(view, command(view), now=NOW - timedelta(seconds=1))
    with pytest.raises(JobConflictError):
        start_transition(view, replace(command(view), expected_version=2), now=NOW)
