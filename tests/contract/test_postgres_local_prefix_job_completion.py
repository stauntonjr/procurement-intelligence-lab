"""Atomic current-attempt success, original retention and stale-writer exclusion."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from threading import Event
from typing import Any

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.runner import run_prefix
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    JobStatus,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobConflictError,
    JobFencedError,
    JobIntegrityError,
    JobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError
from tests.contract.test_postgres_local_prefix_jobs import first, ready
from tests.local_prefix_job_fixtures import NOW, job_input


def candidate(prepared: Any, job: Any, *, seconds: int = 0):
    return CompletedPrefixSnapshot.from_execution(
        run_prefix(prepared, clock=lambda: NOW + timedelta(seconds=seconds)).receipt,
        job.definition.normalization_parameters,
    )


def counts(dsn: str):
    with psycopg.connect(dsn) as conn:
        return (
            conn.execute("SELECT COUNT(*) FROM pil_archive_batches").fetchone(),
            conn.execute("SELECT COUNT(*) FROM pil_archive_content").fetchone(),
            conn.execute("SELECT COUNT(*) FROM pil_planned_executions").fetchone(),
        )


def test_complete_binds_current_receipt_source_archive_and_job_atomically(
    archive_dsn: str, tmp_path: Path
):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    claim = jobs.start(first(job), now=NOW)
    completed = candidate(p, job)
    receipt = jobs.complete(claim.token, completed, content, now=NOW)
    assert receipt.transition.status is JobStatus.SUCCEEDED
    assert receipt.transition.success is not None
    assert (
        receipt.transition.success.completed.execution.receipt_digest
        == completed.execution.receipt_digest
    )
    fresh = bootstrap.build_local_prefix_jobs(archive_dsn)
    assert canonical(fresh.load(job.scope, job.job_id).latest) == canonical(receipt)
    assert fresh.content(job.scope, job.job_id) == content
    assert canonical(
        jobs.complete(claim.token, completed, content, now=NOW + timedelta(seconds=1))
    ) == canonical(receipt)
    with pytest.raises(JobConflictError):
        jobs.complete(
            claim.token, candidate(p, job, seconds=1), content, now=NOW + timedelta(seconds=1)
        )
    with pytest.raises(JobConflictError):
        jobs.start(first(job, "retry", 3, StartIntent.RETRY), now=NOW)


def test_distinct_jobs_share_computation_not_current_receipt(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    old = candidate(p, job)
    retained = jobs.archive.append(old, content)
    for n in range(2):
        current_job = replace(job, idempotency_key=str(n))
        jobs.submit(current_job, now=NOW)
        claim = jobs.start(first(current_job), now=NOW)
        c = candidate(p, job, seconds=n + 1)
        receipt = jobs.complete(claim.token, c, content, now=NOW + timedelta(seconds=n + 1))
        assert receipt.transition.success is not None
        assert (
            receipt.transition.success.completed.execution.receipt_digest
            != retained.receipt.retained_receipt_digest
        )
        assert canonical(receipt.transition.success.retained) == canonical(retained.receipt)
    assert counts(archive_dsn) == ((1,), (1,), (1,))


@pytest.mark.parametrize(
    "table",
    [
        "pil_archive_batches",
        "pil_planned_executions",
        "pil_local_prefix_job_transitions",
        "pil_local_prefix_job_heads",
    ],
)
def test_mid_completion_failure_rolls_back_all_new_evidence(
    archive_dsn: str, tmp_path: Path, table: str
):
    from psycopg import sql

    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION reject_job_commit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected private failure'; END; $$"
        )
        event = sql.SQL("UPDATE") if table.endswith("heads") else sql.SQL("INSERT")
        conn.execute(
            sql.SQL(
                "CREATE TRIGGER reject_job_commit BEFORE {} ON {} FOR EACH ROW EXECUTE FUNCTION reject_job_commit()"
            ).format(event, sql.Identifier(table))
        )
    with pytest.raises(JobUnavailableError):
        jobs.complete(token, candidate(p, job), content, now=NOW)
    assert counts(archive_dsn) == ((0,), (0,), (0,))
    assert jobs.load(job.scope, job.job_id).status is JobStatus.RUNNING


@pytest.mark.parametrize("winner", ["complete", "abandon"])
def test_abandon_and_completion_serialize_before_source_writes(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winner: str
):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    completed = candidate(p, job)
    command = AbandonAttemptCommand(
        job.scope, job.job_id, "abandon", "developer", 2, token.attempt_id, "unresolved process"
    )
    locked = Event()
    release = Event()
    original = jobs._load  # pyright: ignore[reportPrivateUsage]

    def load(*args: Any, **kwargs: Any):
        result = original(*args, **kwargs)
        if kwargs.get("lock") and not locked.is_set():
            locked.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(jobs, "_load", load)

    def complete():
        return jobs.complete(token, completed, content, now=NOW)

    def abandon():
        return jobs.abandon(command, now=NOW)

    with ThreadPoolExecutor(2) as pool:
        first_future = pool.submit(complete if winner == "complete" else abandon)
        assert locked.wait(10)
        second_future = pool.submit(abandon if winner == "complete" else complete)
        release.set()
        first_future.result(timeout=10)
        with pytest.raises(JobConflictError if winner == "complete" else JobFencedError):
            second_future.result(timeout=10)
    view = jobs.load(job.scope, job.job_id)
    assert view.status is (JobStatus.SUCCEEDED if winner == "complete" else JobStatus.ABANDONED)
    if winner == "abandon":
        assert counts(archive_dsn) == ((0,), (0,), (0,))
        retry = jobs.start(first(job, "retry", 3, StartIntent.RETRY), now=NOW)
        with pytest.raises(JobFencedError):
            jobs.complete(token, completed, content, now=NOW)
        assert jobs.load(job.scope, job.job_id).version == retry.receipt.transition.version
        assert counts(archive_dsn) == ((0,), (0,), (0,))


def test_lost_success_acknowledgement_never_proves_rollback(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    original = jobs.archive.source._connection  # pyright: ignore[reportPrivateUsage]

    @contextmanager
    def commit_then_lose_ack():
        with original() as conn:
            yield conn
        raise ArchiveUnavailableError("injected after commit")

    monkeypatch.setattr(jobs.archive.source, "_connection", commit_then_lose_ack)
    with pytest.raises(JobUnavailableError):
        jobs.complete(token, candidate(p, job), content, now=NOW)
    fresh = bootstrap.build_local_prefix_jobs(archive_dsn)
    assert fresh.load(job.scope, job.job_id).status is JobStatus.SUCCEEDED
    assert fresh.content(job.scope, job.job_id) == content


def test_invalid_bytes_on_terminal_replay_are_not_hidden(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    c = candidate(p, job)
    jobs.complete(token, c, content, now=NOW)
    from procurement_intelligence_lab.platform.processing.errors import JobContractError

    with pytest.raises(JobContractError):
        jobs.complete(token, c, content + b"changed", now=NOW)


def test_missing_bound_archive_is_integrity_failure(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    jobs.complete(token, candidate(p, job), content, now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "ALTER TABLE pil_planned_executions DISABLE TRIGGER pil_planned_execution_immutable"
        )
        conn.execute("DELETE FROM pil_planned_executions")
    with pytest.raises(JobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(JobIntegrityError):
        jobs.history(job.scope, job.job_id)
    with pytest.raises(JobIntegrityError):
        jobs.content(job.scope, job.job_id)


def test_failure_and_abandonment_have_one_terminal_winner(archive_dsn: str, tmp_path: Path):
    from threading import Barrier

    from procurement_intelligence_lab.platform.processing.contracts import JobFailure
    from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode

    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    abandon = AbandonAttemptCommand(
        job.scope, job.job_id, "abandon", "developer", 2, token.attempt_id, "unresolved process"
    )
    failure = JobFailure(
        ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE, ErrorCategory.INFRASTRUCTURE, "source_unavailable"
    )
    barrier = Barrier(2)

    def race(kind: str):
        barrier.wait()
        try:
            return (
                jobs.fail(token, failure, now=NOW)
                if kind == "fail"
                else jobs.abandon(abandon, now=NOW)
            )
        except JobConflictError:
            return None

    with ThreadPoolExecutor(2) as pool:
        receipts = list(pool.map(race, ["fail", "abandon"]))
    assert sum(r is not None for r in receipts) == 1
    assert jobs.load(job.scope, job.job_id).status in (JobStatus.FAILED, JobStatus.ABANDONED)
    assert jobs.load(job.scope, job.job_id).version == 3
    assert counts(archive_dsn) == ((0,), (0,), (0,))


def test_success_without_acknowledged_start_is_integrity_failure(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    jobs.complete(token, candidate(p, job), content, now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_local_prefix_job_commands DISABLE TRIGGER USER")
        conn.execute("ALTER TABLE pil_local_prefix_job_transitions DISABLE TRIGGER USER")
        conn.execute("DELETE FROM pil_local_prefix_job_commands")
        conn.execute("DELETE FROM pil_local_prefix_job_transitions WHERE sequence=2")
    with pytest.raises(JobIntegrityError):
        jobs.load(job.scope, job.job_id)
