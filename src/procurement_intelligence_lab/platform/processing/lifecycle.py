"""Pure transition rules; serialization and command replay belong to the journal."""

from datetime import datetime

from procurement_intelligence_lab.platform.execution.identity import aware, digest, same
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    AttemptSuccess,
    AttemptToken,
    JobDefinition,
    JobFailure,
    JobStatus,
    JobTransition,
    JobView,
    StartAttemptCommand,
    StartIntent,
    TransitionKind,
    integer,
    require,
)
from procurement_intelligence_lab.platform.processing.errors import JobConflictError, JobFencedError


def submission_transition(job: JobDefinition, *, now: datetime) -> JobTransition:
    aware(now)
    q = job.definition.request
    require(
        q.source.observed_at <= q.captured_at <= now
        and q.context.started_at <= now
        and job.arrival.announced_at <= now
    )
    return JobTransition(
        job.scope, job.job_id, 1, 1, TransitionKind.SUBMITTED, JobStatus.SUBMITTED, now
    )


def clock(view: JobView, now: datetime) -> None:
    aware(now)
    require(now >= view.latest.transition.recorded_at)
    integer(view.version + 1)


def command_version(view: JobView, command: StartAttemptCommand | AbandonAttemptCommand) -> None:
    if (
        not same(command.scope, view.definition.scope)
        or command.job_id != view.definition.job_id
        or command.expected_version != view.version
    ):
        raise JobConflictError("job command does not match current version")


def start_transition(
    view: JobView, command: StartAttemptCommand, *, now: datetime
) -> JobTransition:
    clock(view, now)
    command_version(view, command)
    allowed = (view.status is JobStatus.SUBMITTED and command.intent is StartIntent.FIRST) or (
        view.status in (JobStatus.FAILED, JobStatus.ABANDONED)
        and command.intent is StartIntent.RETRY
    )
    if not allowed:
        raise JobConflictError(
            "job requires explicit first attempt or retry from an eligible state"
        )
    previous = view.latest.transition.attempt
    ordinal = previous.ordinal + 1 if previous else 1
    fence = previous.fence + (2 if view.status is JobStatus.ABANDONED else 1) if previous else 1
    token = AttemptToken(
        command.scope,
        command.job_id,
        "local-prefix-attempt-v1:" + digest((command.scope, command.job_id, ordinal)),
        ordinal,
        fence,
    )
    return JobTransition(
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


def active(view: JobView, token: AttemptToken) -> None:
    if view.status is not JobStatus.RUNNING or not same(token, view.latest.transition.attempt):
        raise JobFencedError("attempt no longer has publication rights")


def abandon_transition(
    view: JobView, command: AbandonAttemptCommand, *, now: datetime
) -> JobTransition:
    clock(view, now)
    command_version(view, command)
    token = view.latest.transition.attempt
    if (
        view.status is not JobStatus.RUNNING
        or token is None
        or command.attempt_id != token.attempt_id
    ):
        raise JobConflictError("abandon requires the exact active attempt")
    integer(token.fence + 1)
    return JobTransition(
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
    view: JobView, token: AttemptToken, failure: JobFailure, *, now: datetime
) -> JobTransition:
    active(view, token)
    clock(view, now)
    return JobTransition(
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
    view: JobView, token: AttemptToken, success: AttemptSuccess, *, now: datetime
) -> JobTransition:
    active(view, token)
    clock(view, now)
    require(success.completed.execution.completed_at <= now)
    return JobTransition(
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
