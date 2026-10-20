"""Additive append-only Postgres journal over immutable archived assertion membership."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg
from psycopg.rows import dict_row

from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewDecision,
    DocumentReviewTask,
    ReviewDecisionCommand,
    ReviewHistory,
    ReviewProposal,
    aware,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
    ReviewConflictError,
    ReviewContractError,
    ReviewIntegrityError,
    ReviewNotFoundError,
    ReviewUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.assertion_archive import AssertionArchive

_SCHEMA = (
    "CREATE TABLE pil_document_review_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_document_review_meta VALUES (1,1)",
    "CREATE TABLE pil_document_review_tasks (scope TEXT NOT NULL, task_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, assertion_id TEXT NOT NULL, command_hash TEXT NOT NULL, task_digest TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, PRIMARY KEY(scope,task_id), FOREIGN KEY(scope,snapshot_id,assertion_id) REFERENCES pil_archive_members(scope,snapshot_id,assertion_id))",
    "CREATE TABLE pil_document_review_decisions (scope TEXT NOT NULL, task_id TEXT NOT NULL, decision_id TEXT NOT NULL, command_hash TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, PRIMARY KEY(scope,decision_id), UNIQUE(scope,task_id), FOREIGN KEY(scope,task_id) REFERENCES pil_document_review_tasks(scope,task_id))",
    *(
        f"CREATE TRIGGER pil_document_review_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in (
            "pil_document_review_meta",
            "pil_document_review_tasks",
            "pil_document_review_decisions",
        )
    ),
)


def _scope(scope: StateScope) -> str:
    return stable_id("archive-scope-v1", scope)


def checksum(payload: str) -> str:
    return sha256(payload.encode()).hexdigest()


class PostgresDocumentReviewJournal:
    def __init__(self, dsn: str, codec: SemanticCodec, archive: AssertionArchive) -> None:
        self._dsn, self.codec, self.archive = dsn, codec, archive

    @contextmanager
    def _connection(self) -> Generator[psycopg.Connection[dict[str, Any]]]:
        try:
            with psycopg.Connection[dict[str, Any]].connect(
                self._dsn, connect_timeout=5, row_factory=dict_row
            ) as conn:
                conn.execute("SET LOCAL statement_timeout='10s'")
                conn.execute("SET LOCAL lock_timeout='5s'")
                yield conn
        except psycopg.Error:
            raise ReviewUnavailableError(
                "review backend is unavailable or not explicitly initialized"
            ) from None

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        if conn.execute("SELECT singleton,version FROM pil_document_review_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise ReviewIntegrityError("unsupported document-review schema")
        if conn.execute("SELECT singleton,version FROM pil_archive_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise ReviewIntegrityError("review requires compatible archive schema1")

    def initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725125)")
            if conn.execute("SELECT singleton,version FROM pil_archive_meta").fetchall() != [
                {"singleton": 1, "version": 1}
            ]:
                raise ReviewIntegrityError("review requires initialized archive schema1")
            row = conn.execute("SELECT to_regclass('pil_document_review_meta') AS name").fetchone()
            if row is not None and row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)
            conn.execute(
                "SELECT t.scope,t.task_id,t.snapshot_id,t.assertion_id,t.command_hash,t.task_digest,t.payload,t.payload_sha256,d.decision_id,d.command_hash,d.payload,d.payload_sha256 FROM pil_document_review_tasks t LEFT JOIN pil_document_review_decisions d USING(scope,task_id) LIMIT 0"
            )

    def _source(self, proposal: ReviewProposal, *, retained: bool) -> None:
        try:
            _, snapshot = self.archive.load(proposal.scope, proposal.snapshot_id)
        except ArchiveUnavailableError:
            raise ReviewUnavailableError("review source backend is unavailable") from None
        except (ArchiveIntegrityError, ArchiveNotFoundError):
            if retained:
                raise ReviewIntegrityError("retained review source is absent or invalid") from None
            raise ReviewNotFoundError("review requires a valid scoped archived snapshot") from None
        original = next(
            (
                claim
                for claim in snapshot.assertions
                if claim.assertion_id == proposal.previous.assertion_id
            ),
            None,
        )
        if original is None or self.codec.dumps(original) != self.codec.dumps(proposal.previous):
            if retained:
                raise ReviewIntegrityError("retained review assertion differs from archived source")
            raise ReviewContractError(
                "review assertion must match exact archived snapshot membership"
            )

    def _decode(self, row: dict[str, Any]) -> Any:
        if checksum(row["payload"]) != row["payload_sha256"]:
            raise ReviewIntegrityError("review payload checksum mismatch")
        try:
            return self.codec.loads(row["payload"])
        except (ArchiveIntegrityError, ReviewContractError):
            raise ReviewIntegrityError("stored document review graph is invalid") from None

    def _get(
        self,
        conn: psycopg.Connection[dict[str, Any]],
        scope: StateScope,
        task_id: str,
        as_of: datetime | None = None,
    ) -> ReviewHistory:
        row = conn.execute(
            "SELECT * FROM pil_document_review_tasks WHERE scope=%s AND task_id=%s",
            (_scope(scope), task_id),
        ).fetchone()
        if row is None:
            raise ReviewNotFoundError("review task not found in requested scope")
        task = self._decode(row)
        if (
            type(task) is not DocumentReviewTask
            or task.task_id != task_id
            or task.proposal.scope != scope
            or task.proposal.snapshot_id != row["snapshot_id"]
            or task.proposal.previous.assertion_id != row["assertion_id"]
            or task.digest != row["task_digest"]
            or checksum(self.codec.dumps(task.proposal)) != row["command_hash"]
        ):
            raise ReviewIntegrityError("review task identity, membership or digest mismatch")
        self._source(task.proposal, retained=True)
        if as_of is not None and task.recorded_at > as_of:
            raise ReviewNotFoundError("review task was not recorded at requested as-of")
        row = conn.execute(
            "SELECT * FROM pil_document_review_decisions WHERE scope=%s AND task_id=%s",
            (_scope(scope), task_id),
        ).fetchone()
        decision = None
        if row is not None:
            decision = self._decode(row)
            if (
                type(decision) is not DocumentReviewDecision
                or decision.decision_id != row["decision_id"]
                or checksum(self.codec.dumps(decision.command)) != row["command_hash"]
            ):
                raise ReviewIntegrityError("review decision identity mismatch")
        try:
            result = ReviewHistory(task, decision)
        except ReviewContractError:
            raise ReviewIntegrityError("review decision binding or chronology is invalid") from None
        return (
            ReviewHistory(task, None)
            if decision is not None and as_of is not None and decision.recorded_at > as_of
            else result
        )

    def propose(self, proposal: ReviewProposal, recorded_at: datetime) -> DocumentReviewTask:
        aware(recorded_at)
        self._source(proposal, retained=False)
        command_hash = checksum(self.codec.dumps(proposal))
        with self._connection() as conn:
            self._check(conn)
            conn.execute("LOCK TABLE pil_document_review_tasks IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT command_hash FROM pil_document_review_tasks WHERE scope=%s AND task_id=%s",
                (_scope(proposal.scope), proposal.task_id),
            ).fetchone()
            if row is not None:
                if row["command_hash"] != command_hash:
                    raise ReviewConflictError(
                        "review request identity conflicts with retained proposal"
                    )
                return self._get(conn, proposal.scope, proposal.task_id).task
            task = DocumentReviewTask(proposal, recorded_at)
            payload = self.codec.dumps(task)
            conn.execute(
                "INSERT INTO pil_document_review_tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    _scope(proposal.scope),
                    task.task_id,
                    proposal.snapshot_id,
                    proposal.previous.assertion_id,
                    command_hash,
                    task.digest,
                    payload,
                    checksum(payload),
                ),
            )
            return task

    def decide(
        self, command: ReviewDecisionCommand, recorded_at: datetime
    ) -> DocumentReviewDecision:
        aware(recorded_at)
        command_hash = checksum(self.codec.dumps(command))
        with self._connection() as conn:
            self._check(conn)
            conn.execute("LOCK TABLE pil_document_review_tasks IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT task_id FROM pil_document_review_decisions WHERE scope=%s AND decision_id=%s",
                (_scope(command.scope), command.decision_id),
            ).fetchone()
            if row is not None and row["task_id"] != command.task_id:
                raise ReviewConflictError("decision request identity belongs to another task")
            current = self._get(conn, command.scope, command.task_id)
            if current.decision is not None:
                if current.decision.command != command:
                    raise ReviewConflictError(
                        "review task already has a different terminal decision"
                    )
                return current.decision
            if command.task_digest != current.task.digest:
                raise ReviewConflictError("decision digest does not match the exact review task")
            decision = DocumentReviewDecision(command, recorded_at)
            ReviewHistory(current.task, decision)
            payload = self.codec.dumps(decision)
            conn.execute(
                "INSERT INTO pil_document_review_decisions VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    _scope(command.scope),
                    command.task_id,
                    decision.decision_id,
                    command_hash,
                    payload,
                    checksum(payload),
                ),
            )
            return decision

    def get(self, scope: StateScope, task_id: str, as_of: datetime | None = None) -> ReviewHistory:
        if as_of is not None:
            aware(as_of)
        with self._connection() as conn:
            self._check(conn)
            return self._get(conn, scope, task_id, as_of)

    def history(
        self, scope: StateScope, as_of: datetime | None = None
    ) -> tuple[ReviewHistory, ...]:
        if as_of is not None:
            aware(as_of)
        with self._connection() as conn:
            self._check(conn)
            rows = conn.execute(
                "SELECT task_id FROM pil_document_review_tasks WHERE scope=%s", (_scope(scope),)
            ).fetchall()
            results: list[ReviewHistory] = []
            for row in rows:
                try:
                    results.append(self._get(conn, scope, row["task_id"], as_of))
                except ReviewNotFoundError:
                    continue
            return tuple(
                sorted(results, key=lambda result: (result.task.recorded_at, result.task.task_id))
            )
