"""Real database contracts for admitted jobs, command replay and fenced attempts."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from threading import Barrier, Event
from typing import Any

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.execution.resolution_runner import run_resolved_prefix
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobFailure,
    JobStatus,
    ResolvedAbandonAttemptCommand,
    ResolvedStartAttemptCommand,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobConflictError,
    ResolvedJobFencedError,
    ResolvedJobIntegrityError,
    ResolvedJobNotFoundError,
    ResolvedJobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveUnavailableError,
    ErrorCategory,
    ErrorCode,
)
from tests.local_prefix_job_fixtures import NOW
from tests.resolved_job_fixtures import job_input


def ready(dsn: str):
    source = bootstrap.build_assertion_archive(dsn)
    source.initialize()
    archive = bootstrap.build_planned_execution_archive(dsn)
    archive.initialize()
    resolved = bootstrap.build_resolved_execution_archive(dsn)
    resolved.initialize()
    jobs = bootstrap.build_resolved_prefix_jobs(dsn)
    jobs.initialize()
    return jobs


def first(job: Any, key: str = "start", version: int = 1, intent: StartIntent = StartIntent.FIRST):
    return ResolvedStartAttemptCommand(job.scope, job.job_id, key, "developer", version, intent)


def test_explicit_capability_and_scoped_submission_replay(archive_dsn: str, tmp_path: Path):
    jobs = bootstrap.build_resolved_prefix_jobs(archive_dsn)
    with pytest.raises(ResolvedJobUnavailableError):
        jobs.check_ready()
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    (tmp_path / "source.xlsx").unlink()
    receipt = jobs.submit(job, now=NOW)
    assert receipt.transition.status is JobStatus.SUBMITTED
    assert canonical(jobs.submit(job, now=NOW + timedelta(seconds=1))) == canonical(receipt)
    fresh = bootstrap.build_resolved_prefix_jobs(archive_dsn)
    assert canonical(fresh.load(job.scope, job.job_id).definition) == canonical(job)
    with pytest.raises(ResolvedJobConflictError):
        jobs.submit(replace(job, arrival=replace(job.arrival, expected_byte_length=0)), now=NOW)
    with pytest.raises(ResolvedJobConflictError):
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
    with pytest.raises(ResolvedJobNotFoundError):
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
        except ResolvedJobConflictError:
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
    abandon = ResolvedAbandonAttemptCommand(
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
        with pytest.raises(ResolvedJobConflictError):
            jobs.start(changed, now=NOW)
    failure = JobFailure(
        ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE, ErrorCategory.INFRASTRUCTURE, "source_unavailable"
    )
    with pytest.raises(ResolvedJobFencedError):
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
        conn.execute("UPDATE pil_local_resolved_prefix_job_heads SET version=99")
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.history(job.scope, job.job_id)


def test_full_payload_comparison_even_with_forced_request_digest_collision(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.platform.processing.resolved_contracts import (
        ResolvedJobDefinition,
    )

    monkeypatch.setattr(ResolvedJobDefinition, "request_digest", property(lambda _: "0" * 64))
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    with pytest.raises(ResolvedJobConflictError):
        jobs.submit(replace(job, arrival=replace(job.arrival, expected_byte_length=0)), now=NOW)


def test_submission_write_failure_rolls_back_arrival_job_and_head(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION reject_job_transition() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected private driver text'; END; $$"
        )
        conn.execute(
            "CREATE TRIGGER reject_job_transition BEFORE INSERT ON pil_local_resolved_prefix_job_transitions FOR EACH ROW EXECUTE FUNCTION reject_job_transition()"
        )
    with pytest.raises(ResolvedJobUnavailableError) as failure:
        jobs.submit(job, now=NOW)
    assert "private" not in str(failure.value)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM pil_local_resolved_prefix_jobs").fetchone() == (
            0,
        )
        assert conn.execute(
            "SELECT COUNT(*) FROM pil_local_resolved_prefix_job_arrivals"
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT COUNT(*) FROM pil_local_resolved_prefix_job_heads"
        ).fetchone() == (0,)


def test_command_index_corruption_fails_integrity(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    jobs.start(first(job), now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "ALTER TABLE pil_local_resolved_prefix_job_commands DISABLE TRIGGER pil_local_resolved_prefix_job_immutable"
        )
        conn.execute("UPDATE pil_local_resolved_prefix_job_commands SET sequence=1")
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.start(first(job), now=NOW)


@pytest.mark.parametrize(
    "table",
    ["pil_archive_meta", "pil_planned_execution_meta", "pil_local_resolved_prefix_job_meta"],
)
def test_unsupported_prerequisite_versions_are_typed_job_integrity(archive_dsn: str, table: str):
    from psycopg import sql

    jobs = ready(archive_dsn)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(sql.SQL("ALTER TABLE {} DISABLE TRIGGER USER").format(sql.Identifier(table)))
        conn.execute(sql.SQL("UPDATE {} SET version=99").format(sql.Identifier(table)))
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.check_ready()


def candidate(prepared: Any, job: Any, *, seconds: int = 0):
    return CompletedResolvedPrefixSnapshot.from_execution(
        run_resolved_prefix(prepared, clock=lambda: NOW + timedelta(seconds=seconds)).receipt,
        job.definition.prefix.normalization_parameters,
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
    fresh = bootstrap.build_resolved_prefix_jobs(archive_dsn)
    assert canonical(fresh.load(job.scope, job.job_id).latest) == canonical(receipt)
    assert fresh.content(job.scope, job.job_id) == content
    assert canonical(
        jobs.complete(claim.token, completed, content, now=NOW + timedelta(seconds=1))
    ) == canonical(receipt)
    with pytest.raises(ResolvedJobConflictError):
        jobs.complete(
            claim.token, candidate(p, job, seconds=1), content, now=NOW + timedelta(seconds=1)
        )
    with pytest.raises(ResolvedJobConflictError):
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
        "pil_local_resolved_prefix_job_transitions",
        "pil_local_resolved_prefix_job_heads",
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
    with pytest.raises(ResolvedJobUnavailableError):
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
    command = ResolvedAbandonAttemptCommand(
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
        with pytest.raises(
            ResolvedJobConflictError if winner == "complete" else ResolvedJobFencedError
        ):
            second_future.result(timeout=10)
    view = jobs.load(job.scope, job.job_id)
    assert view.status is (JobStatus.SUCCEEDED if winner == "complete" else JobStatus.ABANDONED)
    if winner == "abandon":
        assert counts(archive_dsn) == ((0,), (0,), (0,))
        retry = jobs.start(first(job, "retry", 3, StartIntent.RETRY), now=NOW)
        with pytest.raises(ResolvedJobFencedError):
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
    original = jobs.archive.prefix.source._connection  # pyright: ignore[reportPrivateUsage]

    @contextmanager
    def commit_then_lose_ack():
        with original() as conn:
            yield conn
        raise ArchiveUnavailableError("injected after commit")

    monkeypatch.setattr(jobs.archive.prefix.source, "_connection", commit_then_lose_ack)
    with pytest.raises(ResolvedJobUnavailableError):
        jobs.complete(token, candidate(p, job), content, now=NOW)
    fresh = bootstrap.build_resolved_prefix_jobs(archive_dsn)
    assert fresh.load(job.scope, job.job_id).status is JobStatus.SUCCEEDED
    assert fresh.content(job.scope, job.job_id) == content


def test_invalid_bytes_on_terminal_replay_are_not_hidden(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    c = candidate(p, job)
    jobs.complete(token, c, content, now=NOW)
    from procurement_intelligence_lab.platform.processing.resolved_errors import (
        ResolvedJobContractError,
    )

    with pytest.raises(ResolvedJobContractError):
        jobs.complete(token, c, content + b"changed", now=NOW)


def test_missing_bound_archive_is_integrity_failure(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    jobs.complete(token, candidate(p, job), content, now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "ALTER TABLE pil_resolved_executions DISABLE TRIGGER pil_resolved_execution_immutable"
        )
        conn.execute("DELETE FROM pil_resolved_executions")
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.history(job.scope, job.job_id)
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.content(job.scope, job.job_id)


def test_failure_and_abandonment_have_one_terminal_winner(archive_dsn: str, tmp_path: Path):
    from threading import Barrier

    from procurement_intelligence_lab.platform.processing.resolved_contracts import JobFailure
    from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode

    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    abandon = ResolvedAbandonAttemptCommand(
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
        except ResolvedJobConflictError:
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
        conn.execute("ALTER TABLE pil_local_resolved_prefix_job_commands DISABLE TRIGGER USER")
        conn.execute("ALTER TABLE pil_local_resolved_prefix_job_transitions DISABLE TRIGGER USER")
        conn.execute("DELETE FROM pil_local_resolved_prefix_job_commands")
        conn.execute("DELETE FROM pil_local_resolved_prefix_job_transitions WHERE sequence=2")
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.load(job.scope, job.job_id)


def test_stale_but_consistent_head_cannot_hide_committed_success(archive_dsn: str, tmp_path: Path):

    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    with psycopg.connect(archive_dsn) as conn:
        prior = conn.execute(
            "SELECT sequence,version,status,attempt_id,fence,recorded_at FROM pil_local_resolved_prefix_job_heads"
        ).fetchone()
    assert prior is not None
    jobs.complete(token, candidate(p, job), content, now=NOW)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "UPDATE pil_local_resolved_prefix_job_heads SET sequence=%s,version=%s,status=%s,attempt_id=%s,fence=%s,recorded_at=%s",
            prior,
        )
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.load(job.scope, job.job_id)
    with pytest.raises(ResolvedJobIntegrityError):
        jobs.history(job.scope, job.job_id)


def test_same_attempt_replay_compares_raw_bytes_even_under_hash_collision(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.platform.processing import binding

    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    c = candidate(p, job)
    jobs.complete(token, c, content, now=NOW)

    class Collision:
        def hexdigest(self) -> str:
            return job.arrival.expected_content_hash

    def colliding(_: bytes):
        return Collision()

    monkeypatch.setattr(binding, "sha256", colliding)
    altered = bytes([content[0] ^ 1]) + content[1:]
    assert len(altered) == len(content) and altered != content
    with pytest.raises(ResolvedJobConflictError):
        jobs.complete(token, c, altered, now=NOW)


def test_equal_instant_different_completion_offset_conflicts(archive_dsn: str, tmp_path: Path):
    from datetime import timezone

    jobs = ready(archive_dsn)
    job, p, content = job_input(tmp_path / "source.xlsx")
    jobs.submit(job, now=NOW)
    token = jobs.start(first(job), now=NOW).token
    c = candidate(p, job)
    receipt = jobs.complete(token, c, content, now=NOW)
    shifted = replace(
        c.execution, completed_at=c.execution.completed_at.astimezone(timezone(timedelta(hours=1)))
    )
    assert shifted.completed_at == c.execution.completed_at
    assert shifted.receipt_digest != c.execution.receipt_digest
    changed = CompletedResolvedPrefixSnapshot.from_execution(
        shifted, job.definition.prefix.normalization_parameters
    )
    with pytest.raises(ResolvedJobConflictError):
        jobs.complete(token, changed, content, now=NOW)
    assert jobs.load(job.scope, job.job_id).latest == receipt


def test_new_capability_keeps_old_journal_independent(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT to_regclass('pil_local_prefix_job_meta')").fetchone() == (None,)
    from tests.local_prefix_job_fixtures import job_input as old_input

    old = bootstrap.build_local_prefix_jobs(archive_dsn)
    old.initialize()
    old_job, _, _ = old_input(tmp_path / "old.xlsx")
    new_job, _, _ = job_input(tmp_path / "new.xlsx")
    old.submit(old_job, now=NOW)
    jobs.submit(new_job, now=NOW)
    assert old.load(old_job.scope, old_job.job_id).status is JobStatus.SUBMITTED
    assert jobs.load(new_job.scope, new_job.job_id).status is JobStatus.SUBMITTED


@pytest.mark.parametrize("checkpoint", ["source", "prefix", "resolved", "journal"])
def test_every_publication_checkpoint_rolls_back_all_new_evidence(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str
):
    jobs = ready(archive_dsn)
    job, p, raw = job_input(tmp_path)
    jobs.submit(job, now=NOW)
    claim = jobs.start(first(job), now=NOW)
    done = candidate(p, job)
    if checkpoint == "journal":
        import procurement_intelligence_lab.adapters.postgres_resolved_prefix_jobs as target

        name = "append_transition"
    else:
        target = (
            jobs.archive.prefix.source
            if checkpoint == "source"
            else jobs.archive.prefix
            if checkpoint == "prefix"
            else jobs.archive
        )
        name = "_append_in_transaction"
    original = getattr(target, name)

    def fail_after(*args: Any, **kwargs: Any):
        original(*args, **kwargs)
        raise ArchiveUnavailableError("synthetic publication failure")

    monkeypatch.setattr(target, name, fail_after)
    with pytest.raises(ResolvedJobUnavailableError):
        jobs.complete(claim.token, done, raw, now=NOW)
    assert jobs.load(job.scope, job.job_id).status is JobStatus.RUNNING
    with psycopg.connect(archive_dsn) as conn:
        for table in (
            "pil_archive_batches",
            "pil_archive_content",
            "pil_planned_executions",
            "pil_resolved_executions",
        ):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)


def test_raw_catalog_is_request_evidence_and_first_retention_stays_separate(
    archive_dsn: str, tmp_path: Path
):
    import json

    from procurement_intelligence_lab.platform.execution.resolution_inputs import (
        load_candidate_input,
    )

    jobs = ready(archive_dsn)
    job, prepared, raw = job_input(tmp_path)
    jobs.submit(job, now=NOW)
    original = candidate(prepared, job)
    token = jobs.start(first(job), now=NOW).token
    first_receipt = jobs.complete(token, original, raw, now=NOW)
    wire = json.dumps(json.loads(job.definition.candidate_input.raw_json), indent=2).encode()
    changed = replace(
        job, definition=replace(job.definition, candidate_input=load_candidate_input(wire))
    )
    with pytest.raises(ResolvedJobConflictError):
        jobs.submit(changed, now=NOW)
    other = replace(changed, idempotency_key="separate-full-request")
    service = bootstrap.build_resolved_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    current = candidate(service.prepare_stored(other.definition), other, seconds=1)
    assert current.execution_digest == original.execution_digest
    jobs.submit(other, now=NOW)
    other_token = jobs.start(first(other), now=NOW).token
    receipt = jobs.complete(other_token, current, raw, now=NOW + timedelta(seconds=1))
    assert receipt.transition.success is not None and first_receipt.transition.success is not None
    assert receipt.transition.success.completed.execution.candidate_input.raw_json == wire
    assert receipt.transition.success.retained == first_receipt.transition.success.retained
    assert (
        receipt.transition.success.retained.retained_receipt_digest
        != current.execution.receipt_digest
    )
    assert jobs.load(other.scope, other.job_id).latest == receipt
    retained = jobs.archive.load(other.scope, current.execution_digest)
    assert (
        retained.completed.execution.candidate_input.raw_json
        == original.execution.candidate_input.raw_json
    )
