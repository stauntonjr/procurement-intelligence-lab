"""Explicit local-prefix journal capability using scoped immutable evidence and CAS heads."""

# Cooperating adapters share an existing transaction and bounded codec.
# pyright: reportPrivateUsage=false
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from typing import Any, LiteralString, TypeVar, cast

import psycopg

from procurement_intelligence_lab.adapters.postgres_local_prefix_job_writes import (
    append_transition,
    write_definition,
)
from procurement_intelligence_lab.adapters.postgres_planned_execution_archive import (
    PostgresPlannedExecutionArchive,
)
from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.execution.archive import (
    CompletedPrefixSnapshot,
    same_computation,
)
from procurement_intelligence_lab.platform.execution.identity import canonical, same
from procurement_intelligence_lab.platform.processing.binding import validate_completion
from procurement_intelligence_lab.platform.processing.contracts import (
    AbandonAttemptCommand,
    ArtifactArrival,
    AttemptSuccess,
    AttemptToken,
    JobDefinition,
    JobFailure,
    JobHistoryPage,
    JobJournalReceipt,
    JobStatus,
    JobTransition,
    JobView,
    StartAttemptCommand,
    StartClaim,
    history_bounds,
)
from procurement_intelligence_lab.platform.processing.errors import (
    JobConflictError,
    JobContractError,
    JobIntegrityError,
    JobNotFoundError,
    JobUnavailableError,
)
from procurement_intelligence_lab.platform.processing.lifecycle import (
    abandon_transition,
    active,
    failure_transition,
    start_transition,
    submission_transition,
    success_transition,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveUnavailableError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

_SCHEMA = (
    "CREATE TABLE pil_local_prefix_job_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL)",
    "INSERT INTO pil_local_prefix_job_meta VALUES(1,1)",
    "CREATE TABLE pil_local_prefix_job_arrivals(scope TEXT NOT NULL,event_id TEXT NOT NULL,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(scope,event_id))",
    "CREATE TABLE pil_local_prefix_jobs(scope TEXT NOT NULL,job_id TEXT NOT NULL,request_digest TEXT NOT NULL,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(scope,job_id))",
    "CREATE TABLE pil_local_prefix_job_transitions(scope TEXT NOT NULL,job_id TEXT NOT NULL,sequence BIGINT NOT NULL,record_id TEXT NOT NULL,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(scope,job_id,sequence),FOREIGN KEY(scope,job_id) REFERENCES pil_local_prefix_jobs(scope,job_id))",
    "CREATE TABLE pil_local_prefix_job_commands(scope TEXT NOT NULL,job_id TEXT NOT NULL,family TEXT NOT NULL,command_key TEXT NOT NULL,sequence BIGINT NOT NULL,PRIMARY KEY(scope,job_id,family,command_key),FOREIGN KEY(scope,job_id,sequence) REFERENCES pil_local_prefix_job_transitions(scope,job_id,sequence))",
    "CREATE TABLE pil_local_prefix_job_heads(scope TEXT NOT NULL,job_id TEXT NOT NULL,sequence BIGINT NOT NULL,version BIGINT NOT NULL,status TEXT NOT NULL,attempt_id TEXT,fence BIGINT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(scope,job_id),FOREIGN KEY(scope,job_id,sequence) REFERENCES pil_local_prefix_job_transitions(scope,job_id,sequence))",
    *(
        f"CREATE TRIGGER pil_local_prefix_job_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in (
            "pil_local_prefix_job_meta",
            "pil_local_prefix_job_arrivals",
            "pil_local_prefix_jobs",
            "pil_local_prefix_job_transitions",
            "pil_local_prefix_job_commands",
        )
    ),
)
T = TypeVar("T")


class PostgresLocalPrefixJobs:
    def __init__(self, archive: PostgresPlannedExecutionArchive, codec: SemanticCodec) -> None:
        self.archive = archive
        self.codec = codec

    @contextmanager
    def _connection(self) -> Generator[psycopg.Connection[dict[str, Any]]]:
        try:
            with self.archive.source._connection() as conn:
                yield conn
        except (ArchiveUnavailableError, psycopg.Error):
            raise JobUnavailableError("local prefix job storage is unavailable") from None

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self.archive._check(conn)
        if conn.execute("SELECT singleton,version FROM pil_local_prefix_job_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise JobIntegrityError("unsupported local prefix job capability")
        conn.execute(
            "SELECT scope,job_id,sequence,version,status,attempt_id,fence,recorded_at FROM pil_local_prefix_job_heads LIMIT 0"
        )
        for table in (
            "pil_local_prefix_job_arrivals",
            "pil_local_prefix_jobs",
            "pil_local_prefix_job_transitions",
            "pil_local_prefix_job_commands",
        ):
            conn.execute(f"SELECT * FROM {table} LIMIT 0")

    def initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725125)")
            self.archive._check(conn)
            row = conn.execute("SELECT to_regclass('pil_local_prefix_job_meta') AS name").fetchone()
            if row is None:
                raise JobIntegrityError("job initialization returned no capability evidence")
            if row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)

    def check_ready(self) -> None:
        with self._connection() as conn:
            self._check(conn)

    def _decode(self, row: dict[str, Any], root: type[T]) -> T:
        try:
            if sha256(row["payload"].encode()).hexdigest() != row["payload_sha256"]:
                raise JobIntegrityError("job payload checksum mismatch")
            value = self.codec.loads(row["payload"])
            if type(value) is not root:
                raise JobIntegrityError("job payload root mismatch")
            return cast(T, value)
        except (SemanticContractError, TypeError, KeyError, AttributeError, UnicodeError):
            raise JobIntegrityError("retained local job evidence is invalid") from None

    def _job(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, job_id: str
    ) -> JobDefinition:
        row = conn.execute(
            "SELECT * FROM pil_local_prefix_jobs WHERE scope=%s AND job_id=%s",
            (canonical(scope).decode(), job_id),
        ).fetchone()
        if row is None:
            raise JobNotFoundError("job not found in requested scope")
        job = self._decode(row, JobDefinition)
        if (
            not same(job.scope, scope)
            or job.job_id != job_id
            or row["request_digest"] != job.request_digest
        ):
            raise JobIntegrityError("job request identity mismatch")
        arrival = conn.execute(
            "SELECT * FROM pil_local_prefix_job_arrivals WHERE scope=%s AND event_id=%s",
            (canonical(scope).decode(), job.arrival.event_id),
        ).fetchone()
        if arrival is None or not same(self._decode(arrival, ArtifactArrival), job.arrival):
            raise JobIntegrityError("job arrival evidence mismatch")
        return job

    def _transition(
        self, conn: psycopg.Connection[dict[str, Any]], job: JobDefinition, sequence: int
    ) -> JobTransition:
        row = conn.execute(
            "SELECT * FROM pil_local_prefix_job_transitions WHERE scope=%s AND job_id=%s AND sequence=%s",
            (canonical(job.scope).decode(), job.job_id, sequence),
        ).fetchone()
        if row is None:
            raise JobIntegrityError("job transition evidence is missing")
        t = self._decode(row, JobTransition)
        if (
            t.job_id != job.job_id
            or not same(t.scope, job.scope)
            or t.sequence != sequence
            or t.record_id != row["record_id"]
        ):
            raise JobIntegrityError("job transition identity mismatch")
        if t.command is not None:
            index = conn.execute(
                "SELECT sequence FROM pil_local_prefix_job_commands WHERE scope=%s AND job_id=%s AND family=%s AND command_key=%s",
                (
                    canonical(job.scope).decode(),
                    job.job_id,
                    t.command.family,
                    t.command.command_key,
                ),
            ).fetchone()
            if index is None or index["sequence"] != sequence:
                raise JobIntegrityError("job command linkage mismatch")
        if t.success is not None:
            try:
                retained = self.archive._load(conn, job.scope, t.success.retained.execution_digest)
                content = self.archive.source._content(conn, retained.completed.snapshot)
                validate_completion(job, t.success.completed, content)
                if not same(retained.receipt, t.success.retained) or not same_computation(
                    t.success.completed, retained.completed
                ):
                    raise JobIntegrityError("successful attempt disagrees with retained execution")
            except SemanticContractError:
                raise JobIntegrityError("successful job evidence is missing or invalid") from None
        return t

    def _load(
        self,
        conn: psycopg.Connection[dict[str, Any]],
        scope: StateScope,
        job_id: str,
        *,
        lock: bool = False,
    ) -> JobView:
        job = self._job(conn, scope, job_id)
        head = conn.execute(
            cast(
                LiteralString,
                "SELECT * FROM pil_local_prefix_job_heads WHERE scope=%s AND job_id=%s"
                + (" FOR UPDATE" if lock else ""),
            ),
            (canonical(scope).decode(), job_id),
        ).fetchone()
        if head is None:
            raise JobIntegrityError("job head evidence is missing")
        t = self._transition(conn, job, head["sequence"])
        token = t.attempt
        expected = (
            t.sequence,
            t.version,
            t.status.value,
            token.attempt_id if token else None,
            (token.fence + (1 if t.status is JobStatus.ABANDONED else 0)) if token else 0,
            t.recorded_at.isoformat(),
        )
        if (
            tuple(
                head[k]
                for k in ("sequence", "version", "status", "attempt_id", "fence", "recorded_at")
            )
            != expected
        ):
            raise JobIntegrityError("job head disagrees with immutable evidence")
        initial = self._transition(conn, job, 1)
        if (
            not same(initial, submission_transition(job, now=initial.recorded_at))
            or t.recorded_at < initial.recorded_at
        ):
            raise JobIntegrityError("job submission linkage mismatch")
        return JobView(job, JobJournalReceipt(t))

    def submit(self, job: JobDefinition, *, now: datetime) -> JobJournalReceipt:
        if type(job) is not JobDefinition:
            raise JobContractError("job submission requires immutable typed inputs")
        transition = submission_transition(job, now=now)
        self.codec.dumps(job)
        with self._connection() as conn:
            self._check(conn)
            # Admission serialization precedes creation; runtime execution holds no lock.
            conn.execute("SELECT pg_advisory_xact_lock(640725126)")
            existing = conn.execute(
                "SELECT job_id FROM pil_local_prefix_jobs WHERE scope=%s AND job_id=%s",
                (canonical(job.scope).decode(), job.job_id),
            ).fetchone()
            if existing is not None:
                retained = self._load(conn, job.scope, job.job_id)
                if not same(retained.definition, job):
                    raise JobConflictError("idempotency key conflicts with retained job inputs")
                return JobJournalReceipt(self._transition(conn, job, 1))
            arrival = conn.execute(
                "SELECT * FROM pil_local_prefix_job_arrivals WHERE scope=%s AND event_id=%s",
                (canonical(job.scope).decode(), job.arrival.event_id),
            ).fetchone()
            if arrival is not None and not same(
                self._decode(arrival, ArtifactArrival), job.arrival
            ):
                raise JobConflictError("arrival event identity conflicts with retained declaration")
            write_definition(conn, self.codec, job)
            append_transition(conn, self.codec, transition)
            return JobJournalReceipt(transition)

    def load(self, scope: StateScope, job_id: str) -> JobView:
        history_bounds(scope, job_id, 1, 0)
        with self._connection() as conn:
            self._check(conn)
            return self._load(conn, scope, job_id)

    def _command_replay(
        self,
        conn: psycopg.Connection[dict[str, Any]],
        view: JobView,
        command: StartAttemptCommand | AbandonAttemptCommand,
    ) -> JobJournalReceipt | None:
        row = conn.execute(
            "SELECT sequence FROM pil_local_prefix_job_commands WHERE scope=%s AND job_id=%s AND family=%s AND command_key=%s",
            (
                canonical(command.scope).decode(),
                command.job_id,
                command.family,
                command.command_key,
            ),
        ).fetchone()
        if row is None:
            return None
        transition = self._transition(conn, view.definition, row["sequence"])
        if not same(transition.command, command):
            raise JobConflictError("command key conflicts with its retained full payload")
        return JobJournalReceipt(transition)

    def start(self, command: StartAttemptCommand, *, now: datetime) -> StartClaim:
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, command.scope, command.job_id, lock=True)
            receipt = self._command_replay(conn, view, command)
            if receipt is not None:
                token = receipt.transition.attempt
                if token is None:
                    raise JobIntegrityError("retained start has no attempt evidence")
                return StartClaim(receipt, token, False)
            transition = start_transition(view, command, now=now)
            append_transition(conn, self.codec, transition)
            assert transition.attempt is not None
            return StartClaim(JobJournalReceipt(transition), transition.attempt, True)

    def abandon(self, command: AbandonAttemptCommand, *, now: datetime) -> JobJournalReceipt:
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, command.scope, command.job_id, lock=True)
            receipt = self._command_replay(conn, view, command)
            if receipt is not None:
                return receipt
            transition = abandon_transition(view, command, now=now)
            append_transition(conn, self.codec, transition)
            return JobJournalReceipt(transition)

    def fail(self, token: AttemptToken, failure: JobFailure, *, now: datetime) -> JobJournalReceipt:
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, token.scope, token.job_id, lock=True)
            previous = view.latest.transition
            if view.status is JobStatus.FAILED and same(previous.attempt, token):
                if not same(previous.failure, failure):
                    raise JobConflictError("attempt failure conflicts with retained outcome")
                return view.latest
            transition = failure_transition(view, token, failure, now=now)
            append_transition(conn, self.codec, transition)
            return JobJournalReceipt(transition)

    def complete(
        self,
        token: AttemptToken,
        completed: CompletedPrefixSnapshot,
        content: bytes,
        *,
        now: datetime,
    ) -> JobJournalReceipt:
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, token.scope, token.job_id, lock=True)
            validate_completion(view.definition, completed, content)
            previous = view.latest.transition
            if view.status is JobStatus.SUCCEEDED and same(previous.attempt, token):
                if previous.success is None or not same(previous.success.completed, completed):
                    raise JobConflictError(
                        "attempt completion conflicts with retained full receipt"
                    )
                return view.latest
            active(view, token)
            retained = self.archive._append_in_transaction(conn, completed, content)
            transition = success_transition(
                view, token, AttemptSuccess(completed, retained.receipt), now=now
            )
            append_transition(conn, self.codec, transition)
            return JobJournalReceipt(transition)

    def history(
        self, scope: StateScope, job_id: str, *, limit: int = 100, after_sequence: int = 0
    ) -> JobHistoryPage:
        history_bounds(scope, job_id, limit, after_sequence)
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, scope, job_id)
            rows = conn.execute(
                "SELECT sequence FROM pil_local_prefix_job_transitions WHERE scope=%s AND job_id=%s AND sequence>%s ORDER BY sequence LIMIT %s",
                (canonical(scope).decode(), job_id, after_sequence, limit + 1),
            ).fetchall()
            receipts = tuple(
                JobJournalReceipt(self._transition(conn, view.definition, r["sequence"]))
                for r in rows[:limit]
            )
            more = len(rows) > limit
            return JobHistoryPage(
                scope,
                job_id,
                after_sequence,
                limit,
                receipts,
                more,
                receipts[-1].transition.sequence if more else None,
            )

    def content(self, scope: StateScope, job_id: str) -> bytes:
        history_bounds(scope, job_id, 1, 0)
        with self._connection() as conn:
            self._check(conn)
            view = self._load(conn, scope, job_id)
            success = view.latest.transition.success
            if success is None:
                raise JobConflictError("job has no positively recorded success")
            return self.archive.source._content(conn, success.completed.snapshot)
