"""Additive planned-prefix capability sharing the source archive's atomic transaction."""

from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg

from procurement_intelligence_lab.adapters.postgres_archive import PostgresAssertionArchive, _scope
from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    ExecutionHistoryPage,
    execution_key,
    history_bounds,
    same_computation,
    scope_contract,
)
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

_SCHEMA = (
    "CREATE TABLE pil_planned_execution_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_planned_execution_meta VALUES (1,1)",
    "CREATE TABLE pil_planned_executions (sequence BIGSERIAL PRIMARY KEY, scope TEXT NOT NULL, execution_digest TEXT NOT NULL, retained_receipt_digest TEXT NOT NULL, snapshot_id TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, UNIQUE(scope,execution_digest), FOREIGN KEY(scope,snapshot_id) REFERENCES pil_archive_batches(scope,snapshot_id))",
    *(
        f"CREATE TRIGGER pil_planned_execution_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in ("pil_planned_execution_meta", "pil_planned_executions")
    ),
)


class PostgresPlannedExecutionArchive:
    def __init__(self, source: PostgresAssertionArchive, codec: SemanticCodec) -> None:
        self.source = source
        self.codec = codec

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self.source._check(conn)
        if conn.execute("SELECT singleton,version FROM pil_planned_execution_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise ArchiveIntegrityError("unsupported planned execution archive capability")
        conn.execute(
            "SELECT sequence,scope,execution_digest,retained_receipt_digest,snapshot_id,payload,payload_sha256 FROM pil_planned_executions LIMIT 0"
        )

    def initialize(self) -> None:
        with self.source._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725124)")
            self.source._check(conn)
            row = conn.execute(
                "SELECT to_regclass('pil_planned_execution_meta') AS name"
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("planned archive initialization produced no metadata")
            if row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)

    def check_ready(self) -> None:
        with self.source._connection() as conn:
            self._check(conn)

    def append(self, completed: CompletedPrefixSnapshot, content: bytes) -> ArchivedPrefix:
        if type(completed) is not CompletedPrefixSnapshot:
            raise ArchiveContractError("planned archive requires a completed typed prefix")
        artifact = completed.snapshot.artifact
        if (
            type(content) is not bytes
            or len(content) != artifact.byte_length
            or sha256(content).hexdigest() != artifact.content_hash
        ):
            raise ArchiveContractError("planned archive requires exact captured bytes")
        payload = self.codec.dumps(completed)
        with self.source._connection() as conn:
            self._check(conn)
            conn.execute("LOCK TABLE pil_archive_batches IN SHARE ROW EXCLUSIVE MODE")
            conn.execute("LOCK TABLE pil_planned_executions IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT execution_digest FROM pil_planned_executions WHERE scope=%s AND execution_digest=%s",
                (_scope(completed.scope), completed.execution_digest),
            ).fetchone()
            if row is not None:
                retained = self._load(conn, completed.scope, completed.execution_digest)
                if (
                    not same_computation(completed, retained.completed)
                    or self.source._content(conn, retained.completed.snapshot) != content
                ):
                    raise ArchiveConflictError(
                        "execution identity conflicts with retained computation"
                    )
                return retained
            source_receipt = self.source._append_in_transaction(conn, completed.snapshot, content)
            row = conn.execute(
                "INSERT INTO pil_planned_executions(scope,execution_digest,retained_receipt_digest,snapshot_id,payload,payload_sha256) VALUES (%s,%s,%s,%s,%s,%s) RETURNING sequence",
                (
                    _scope(completed.scope),
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    completed.snapshot.snapshot_id,
                    payload,
                    sha256(payload.encode()).hexdigest(),
                ),
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("planned archive insert produced no receipt")
            return ArchivedPrefix(
                completed,
                ExecutionArchiveReceipt(
                    row["sequence"],
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    source_receipt,
                ),
            )

    def _load(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, execution_digest: str
    ) -> ArchivedPrefix:
        row = conn.execute(
            "SELECT * FROM pil_planned_executions WHERE scope=%s AND execution_digest=%s",
            (_scope(scope), execution_digest),
        ).fetchone()
        if row is None:
            raise ArchiveNotFoundError("planned execution not found in requested scope")
        if sha256(row["payload"].encode()).hexdigest() != row["payload_sha256"]:
            raise ArchiveIntegrityError("planned execution payload checksum mismatch")
        try:
            completed = self.codec.loads(row["payload"])
            if (
                type(completed) is not CompletedPrefixSnapshot
                or canonical(completed.scope) != canonical(scope)
                or completed.execution_digest != execution_digest
                or completed.execution.receipt_digest != row["retained_receipt_digest"]
                or completed.snapshot.snapshot_id != row["snapshot_id"]
            ):
                raise ArchiveIntegrityError("planned execution identity or scope mismatch")
            source_receipt, snapshot = self.source._load(conn, scope, row["snapshot_id"])
            if canonical(snapshot) != canonical(completed.snapshot):
                raise ArchiveIntegrityError("planned execution source evidence mismatch")
            return ArchivedPrefix(
                completed,
                ExecutionArchiveReceipt(
                    row["sequence"],
                    execution_digest,
                    row["retained_receipt_digest"],
                    source_receipt,
                ),
            )
        except SemanticContractError:
            raise ArchiveIntegrityError("retained planned execution evidence is invalid") from None

    def load(self, scope: StateScope, execution_digest: str) -> ArchivedPrefix:
        scope_contract(scope)
        execution_key(execution_digest)
        with self.source._connection() as conn:
            self._check(conn)
            return self._load(conn, scope, execution_digest)

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ExecutionHistoryPage:
        history_bounds(scope, limit, after_sequence)
        with self.source._connection() as conn:
            self._check(conn)
            rows = conn.execute(
                "SELECT execution_digest FROM pil_planned_executions WHERE scope=%s AND sequence>%s ORDER BY sequence LIMIT %s",
                (_scope(scope), after_sequence, limit + 1),
            ).fetchall()
            receipts = tuple(
                self._load(conn, scope, row["execution_digest"]).receipt for row in rows[:limit]
            )
            more = len(rows) > limit
            return ExecutionHistoryPage(
                scope,
                after_sequence,
                limit,
                receipts,
                more,
                receipts[-1].sequence if more else None,
            )

    def content(self, scope: StateScope, execution_digest: str) -> bytes:
        scope_contract(scope)
        execution_key(execution_digest)
        with self.source._connection() as conn:
            self._check(conn)
            retained = self._load(conn, scope, execution_digest)
            return self.source._content(conn, retained.completed.snapshot)
