"""Real database contracts for admitted jobs, command replay and fenced attempts."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from typing import Any

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    JobFailure,
    JobStatus,
    StartAttemptCommand,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobConflictError,
    JobFencedError,
    JobIntegrityError,
    JobNotFoundError,
    JobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from tests.local_prefix_job_fixtures import NOW, job_input


def ready(dsn: str):
    source = bootstrap.build_assertion_archive(dsn)
    source.initialize()
    archive = bootstrap.build_planned_execution_archive(dsn)
    archive.initialize()
    jobs = bootstrap.build_local_prefix_jobs(dsn)
    jobs.initialize()
    return jobs


def first(job: Any, key: str = "start", version: int = 1, intent: StartIntent = StartIntent.FIRST):
    return StartAttemptCommand(job.scope, job.job_id, key, "developer", version, intent)


def test_explicit_capability_and_scoped_submission_replay(archive_dsn: str, tmp_path: Path):
    jobs = bootstrap.build_local_prefix_jobs(archive_dsn)
    with pytest.raises(JobUnavailableError):
        jobs.check_ready()
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    (tmp_path / "source.xlsx").unlink()
    receipt = jobs.submit(job, now=NOW)
    assert receipt.transition.status is JobStatus.SUBMITTED
    assert canonical(jobs.submit(job, now=NOW + timedelta(seconds=1))) == canonical(receipt)
    fresh = bootstrap.build_local_prefix_jobs(archive_dsn)
    assert canonical(fresh.load(job.scope, job.job_id).definition) == canonical(job)
    with pytest.raises(JobConflictError):
        jobs.submit(replace(job, arrival=replace(job.arrival, expected_byte_length=0)), now=NOW)
    with pytest.raises(JobConflictError):
        jobs.submit(
            replace(
                job,
                idempotency_key="different",
                arrival=replace(job.arrival, expected_byte_length=0),
            ),
            now=NOW,
        )
    other = replace(job, idempotency_key="distinct")
    assert jobs.submit(other, now=NOW).transition.job_id != job.job_id
    with pytest.raises(JobNotFoundError):
        fresh.load(replace(job.scope, project_id="foreign"), job.job_id)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM pil_archive_batches").fetchone() == (0,)


@pytest.mark.parametrize("same", [True, False])
def test_concurrent_claims_execute_only_one_invocation(
    archive_dsn: str, tmp_path: Path, same: bool
):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    barrier = Barrier(6)

    def claim(i: int):
        barrier.wait()
        try:
            return jobs.start(first(job, "same" if same else str(i)), now=NOW)
        except JobConflictError:
            return None

    with ThreadPoolExecutor(6) as pool:
        claims = list(pool.map(claim, range(6)))
    valid = [c for c in claims if c is not None]
    assert sum(c.newly_claimed for c in valid) == 1
    assert len(valid) == (6 if same else 1)
    assert len({c.receipt.transition.record_id for c in valid}) == 1
    assert jobs.load(job.scope, job.job_id).version == 2


def test_command_family_full_payload_and_late_historical_replay(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    command = first(job)
    claim = jobs.start(command, now=NOW)
    abandon = AbandonAttemptCommand(
        job.scope,
        job.job_id,
        "abandon",
        "developer",
        2,
        claim.token.attempt_id,
        "unresolved local process",
    )
    abandoned = jobs.abandon(abandon, now=NOW)
    retry = jobs.start(first(job, "retry", 3, StartIntent.RETRY), now=NOW)
    assert retry.token.ordinal == 2 and retry.token.fence == 3
    assert not jobs.start(command, now=NOW).newly_claimed
    assert canonical(jobs.abandon(abandon, now=NOW)) == canonical(abandoned)
    assert jobs.load(job.scope, job.job_id).version == 4
    for changed in [
        replace(command, intent=StartIntent.RETRY),
        replace(command, actor="different"),
        replace(command, expected_version=4),
    ]:
        with pytest.raises(JobConflictError):
            jobs.start(changed, now=NOW)
    failure = JobFailure(
        ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE, ErrorCategory.INFRASTRUCTURE, "source_unavailable"
    )
    with pytest.raises(JobFencedError):
        jobs.fail(claim.token, failure, now=NOW)
    receipt = jobs.fail(retry.token, failure, now=NOW)
    assert canonical(jobs.fail(retry.token, failure, now=NOW + timedelta(seconds=1))) == canonical(
        receipt
    )
    assert jobs.load(job.scope, job.job_id).status is JobStatus.FAILED
    page = jobs.history(job.scope, job.job_id, limit=2)
    assert len(page.receipts) == 2 and page.has_more and page.next_after_sequence == 2
    tail = jobs.history(job.scope, job.job_id, limit=200, after_sequence=page.next_after_sequence)
    assert [r.transition.sequence for r in tail.receipts] == [3, 4, 5]
    assert not tail.has_more and tail.next_after_sequence is None


def test_head_corruption_never_becomes_success_or_empty(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("UPDATE pil_local_prefix_job_heads SET version=99")
    with pytest.raises(JobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(JobIntegrityError):
        jobs.history(job.scope, job.job_id)


def test_full_payload_comparison_even_with_forced_request_digest_collision(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.platform.processing.contracts import JobDefinition

    monkeypatch.setattr(JobDefinition, "request_digest", property(lambda _: "0" * 64))
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    with pytest.raises(JobConflictError):
        jobs.submit(replace(job, arrival=replace(job.arrival, expected_byte_length=0)), now=NOW)


def test_submission_write_failure_rolls_back_arrival_job_and_head(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION reject_job_transition() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected private driver text'; END; $$"
        )
        conn.execute(
            "CREATE TRIGGER reject_job_transition BEFORE INSERT ON pil_local_prefix_job_transitions FOR EACH ROW EXECUTE FUNCTION reject_job_transition()"
        )
    with pytest.raises(JobUnavailableError) as failure:
        jobs.submit(job, now=NOW)
    assert "private" not in str(failure.value)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM pil_local_prefix_jobs").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM pil_local_prefix_job_arrivals").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM pil_local_prefix_job_heads").fetchone() == (0,)


def test_command_index_corruption_fails_integrity(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    jobs.start(first(job), now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "ALTER TABLE pil_local_prefix_job_commands DISABLE TRIGGER pil_local_prefix_job_immutable"
        )
        conn.execute("UPDATE pil_local_prefix_job_commands SET sequence=1")
    with pytest.raises(JobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(JobIntegrityError):
        jobs.start(first(job), now=NOW)
