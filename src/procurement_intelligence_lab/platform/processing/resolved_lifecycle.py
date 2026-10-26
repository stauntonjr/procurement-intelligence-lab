"""Pure transition rules; serialization and command replay belong to the journal."""

from datetime import datetime

from procurement_intelligence_lab.platform.execution.identity import aware, digest, same
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobFailure,
    JobStatus,
    ResolvedAbandonAttemptCommand,
    ResolvedAttemptSuccess,
    ResolvedAttemptToken,
    ResolvedJobDefinition,
    ResolvedJobTransition,
    ResolvedJobView,
    ResolvedStartAttemptCommand,
    StartIntent,
    TransitionKind,
    integer,
    require,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobConflictError,
    ResolvedJobFencedError,
)


def submission_transition(job: ResolvedJobDefinition, *, now: datetime) -> ResolvedJobTransition:
    aware(now)
    q = job.definition.request
    require(
        q.source.observed_at <= q.captured_at <= now
        and q.context.started_at <= now
        and job.arrival.announced_at <= now
    )
    return ResolvedJobTransition(
        job.scope, job.job_id, 1, 1, TransitionKind.SUBMITTED, JobStatus.SUBMITTED, now
    )


def clock(view: ResolvedJobView, now: datetime) -> None:
    aware(now)
    require(now >= view.latest.transition.recorded_at)
    integer(view.version + 1)


def command_version(
    view: ResolvedJobView, command: ResolvedStartAttemptCommand | ResolvedAbandonAttemptCommand
) -> None:
    if (
        not same(command.scope, view.definition.scope)
        or command.job_id != view.definition.job_id
        or command.expected_version != view.version
    ):
        raise ResolvedJobConflictError("job command does not match current version")


def start_transition(
    view: ResolvedJobView, command: ResolvedStartAttemptCommand, *, now: datetime
) -> ResolvedJobTransition:
    clock(view, now)
    command_version(view, command)
    allowed = (view.status is JobStatus.SUBMITTED and command.intent is StartIntent.FIRST) or (
        view.status in (JobStatus.FAILED, JobStatus.ABANDONED)
        and command.intent is StartIntent.RETRY
    )
    if not allowed:
        raise ResolvedJobConflictError(
            "job requires explicit first attempt or retry from an eligible state"
        )
    previous = view.latest.transition.attempt
    ordinal = previous.ordinal + 1 if previous else 1
    fence = previous.fence + (2 if view.status is JobStatus.ABANDONED else 1) if previous else 1
    token = ResolvedAttemptToken(
        command.scope,
        command.job_id,
        "local-resolved-prefix-attempt-v1:" + digest((command.scope, command.job_id, ordinal)),
        ordinal,
        fence,
    )
    return ResolvedJobTransition(
        command.scope,
        command.job_id,
        view.version + 1,
        view.version + 1,
        TransitionKind.STARTED,
        JobStatus.RUNNING,
        now,
        command,
        token,
    )


def active(view: ResolvedJobView, token: ResolvedAttemptToken) -> None:
    if view.status is not JobStatus.RUNNING or not same(token, view.latest.transition.attempt):
        raise ResolvedJobFencedError("attempt no longer has publication rights")


def abandon_transition(
    view: ResolvedJobView, command: ResolvedAbandonAttemptCommand, *, now: datetime
) -> ResolvedJobTransition:
    clock(view, now)
    command_version(view, command)
    token = view.latest.transition.attempt
    if (
        view.status is not JobStatus.RUNNING
        or token is None
        or command.attempt_id != token.attempt_id
    ):
        raise ResolvedJobConflictError("abandon requires the exact active attempt")
    integer(token.fence + 1)
    return ResolvedJobTransition(
        command.scope,
        command.job_id,
        view.version + 1,
        view.version + 1,
        TransitionKind.ABANDONED,
        JobStatus.ABANDONED,
        now,
        command,
        token,
    )


def failure_transition(
    view: ResolvedJobView, token: ResolvedAttemptToken, failure: JobFailure, *, now: datetime
) -> ResolvedJobTransition:
    active(view, token)
    clock(view, now)
    return ResolvedJobTransition(
        token.scope,
        token.job_id,
        view.version + 1,
        view.version + 1,
        TransitionKind.FAILED,
        JobStatus.FAILED,
        now,
        attempt=token,
        failure=failure,
    )


def success_transition(
    view: ResolvedJobView,
    token: ResolvedAttemptToken,
    success: ResolvedAttemptSuccess,
    *,
    now: datetime,
) -> ResolvedJobTransition:
    active(view, token)
    clock(view, now)
    require(success.completed.execution.completed_at <= now)
    return ResolvedJobTransition(
        token.scope,
        token.job_id,
        view.version + 1,
        view.version + 1,
        TransitionKind.SUCCEEDED,
        JobStatus.SUCCEEDED,
        now,
        attempt=token,
        success=success,
    )
