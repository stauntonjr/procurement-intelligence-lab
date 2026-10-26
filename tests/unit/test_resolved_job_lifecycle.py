"""Pure transition policy: explicit retry, nonregressing clocks and fences."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobFailure,
    JobStatus,
    ResolvedAbandonAttemptCommand,
    ResolvedJobJournalReceipt,
    ResolvedJobView,
    ResolvedStartAttemptCommand,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobConflictError,
    ResolvedJobContractError,
    ResolvedJobFencedError,
)
from procurement_intelligence_lab.platform.processing.resolved_lifecycle import (
    abandon_transition,
    failure_transition,
    start_transition,
    submission_transition,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from tests.local_prefix_job_fixtures import NOW
from tests.resolved_job_fixtures import job_input


def initial(tmp_path: Path) -> ResolvedJobView:
    job, _, _ = job_input(tmp_path)
    return ResolvedJobView(job, ResolvedJobJournalReceipt(submission_transition(job, now=NOW)))


def command(
    view: ResolvedJobView, key: str = "start-1", intent: StartIntent = StartIntent.FIRST
) -> ResolvedStartAttemptCommand:
    return ResolvedStartAttemptCommand(
        view.definition.scope, view.definition.job_id, key, "developer", view.version, intent
    )


def test_transition_matrix_and_historical_command_payload(tmp_path: Path) -> None:
    view = initial(tmp_path)
    started = start_transition(view, command(view), now=NOW)
    running = ResolvedJobView(view.definition, ResolvedJobJournalReceipt(started))
    assert running.status is JobStatus.RUNNING and running.version == 2
    with pytest.raises(ResolvedJobConflictError):
        start_transition(running, command(running), now=NOW)
    token = started.attempt
    assert token is not None
    abandoned = abandon_transition(
        running,
        ResolvedAbandonAttemptCommand(
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
    stopped = ResolvedJobView(view.definition, ResolvedJobJournalReceipt(abandoned))
    retry = start_transition(stopped, command(stopped, "retry-1", StartIntent.RETRY), now=NOW)
    assert retry.attempt is not None
    assert retry.attempt.ordinal == 2 and retry.attempt.fence > token.fence
    assert retry.attempt.attempt_id != token.attempt_id
    assert isinstance(retry.command, ResolvedStartAttemptCommand)
    assert retry.command.intent is StartIntent.RETRY
    assert (
        view.definition.definition.prefix.effective_context
        == running.definition.definition.prefix.effective_context
    )
    with pytest.raises(ResolvedJobFencedError):
        failure_transition(
            ResolvedJobView(view.definition, ResolvedJobJournalReceipt(retry)),
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
    running = ResolvedJobView(
        view.definition, ResolvedJobJournalReceipt(start_transition(view, command(view), now=NOW))
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
    failed_view = ResolvedJobView(view.definition, ResolvedJobJournalReceipt(failed))
    with pytest.raises(ResolvedJobConflictError):
        start_transition(failed_view, command(failed_view), now=NOW)
    retried = start_transition(failed_view, command(failed_view, intent=StartIntent.RETRY), now=NOW)
    assert retried.attempt is not None and retried.attempt.ordinal == 2


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, 2**63])
def test_counter_time_and_scope_boundaries(tmp_path: Path, value: object) -> None:
    view = initial(tmp_path)
    with pytest.raises(ResolvedJobContractError):
        replace(command(view), expected_version=value)


def test_future_arrival_regressing_clock_and_stale_version(tmp_path: Path) -> None:
    view = initial(tmp_path)
    with pytest.raises(ResolvedJobContractError):
        submission_transition(
            replace(
                view.definition,
                arrival=replace(view.definition.arrival, announced_at=NOW + timedelta(seconds=1)),
            ),
            now=NOW,
        )
    with pytest.raises(ResolvedJobContractError):
        start_transition(view, command(view), now=NOW - timedelta(seconds=1))
    with pytest.raises(ResolvedJobConflictError):
        start_transition(view, replace(command(view), expected_version=2), now=NOW)


@pytest.mark.parametrize("resolved", [False, True])
def test_same_explicit_lifecycle_policy_for_both_profiles(tmp_path: Path, resolved: bool):
    from typing import Any

    from procurement_intelligence_lab.platform.processing import contracts as old
    from procurement_intelligence_lab.platform.processing import lifecycle as old_rules
    from procurement_intelligence_lab.platform.processing import resolved_contracts as new
    from procurement_intelligence_lab.platform.processing import resolved_lifecycle as new_rules
    from tests.local_prefix_job_fixtures import job_input as old_input

    c: Any = new if resolved else old
    rules: Any = new_rules if resolved else old_rules
    make: Any = job_input if resolved else old_input
    job, _, _ = make(tmp_path / "resolved" if resolved else tmp_path / "old.xlsx")
    View: Any = c.ResolvedJobView if resolved else c.JobView
    Receipt: Any = c.ResolvedJobJournalReceipt if resolved else c.JobJournalReceipt
    Start: Any = c.ResolvedStartAttemptCommand if resolved else c.StartAttemptCommand
    Abandon: Any = c.ResolvedAbandonAttemptCommand if resolved else c.AbandonAttemptCommand
    view = View(job, Receipt(rules.submission_transition(job, now=NOW)))
    t = rules.start_transition(
        view, Start(job.scope, job.job_id, "first", "developer", 1, c.StartIntent.FIRST), now=NOW
    )
    assert (t.version, t.sequence, t.attempt.ordinal, t.attempt.fence) == (2, 2, 1, 1)
    stopped = rules.abandon_transition(
        View(job, Receipt(t)),
        Abandon(
            job.scope, job.job_id, "abandon", "developer", 2, t.attempt.attempt_id, "unresolved"
        ),
        now=NOW,
    )
    retry = rules.start_transition(
        View(job, Receipt(stopped)),
        Start(job.scope, job.job_id, "retry", "developer", 3, c.StartIntent.RETRY),
        now=NOW,
    )
    assert (retry.version, retry.sequence, retry.attempt.ordinal, retry.attempt.fence) == (
        4,
        4,
        2,
        3,
    )
