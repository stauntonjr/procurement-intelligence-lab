"""Explicit additive capability; source, prefix and sixth publication share one transaction."""
# pyright: reportPrivateUsage=false

from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg

from procurement_intelligence_lab.adapters.postgres_archive import _scope
from procurement_intelligence_lab.adapters.postgres_planned_execution_archive import (
    PostgresPlannedExecutionArchive,
)
from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.execution.archive import (
    execution_key,
    history_bounds,
    scope_contract,
)
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
    CompletedResolvedPrefixSnapshot,
    ResolvedExecutionArchiveReceipt,
    ResolvedExecutionHistoryPage,
    same_resolved_computation,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

_SCHEMA = (
    "CREATE TABLE pil_resolved_execution_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_resolved_execution_meta VALUES (1,1)",
    "CREATE TABLE pil_resolved_executions (sequence BIGSERIAL PRIMARY KEY, scope TEXT NOT NULL, execution_digest TEXT NOT NULL, retained_receipt_digest TEXT NOT NULL, snapshot_id TEXT NOT NULL, prefix_execution_digest TEXT NOT NULL, retained_prefix_receipt_digest TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, UNIQUE(scope,execution_digest), FOREIGN KEY(scope,prefix_execution_digest) REFERENCES pil_planned_executions(scope,execution_digest), FOREIGN KEY(scope,snapshot_id) REFERENCES pil_archive_batches(scope,snapshot_id))",
    *(
        f"CREATE TRIGGER pil_resolved_execution_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in ("pil_resolved_execution_meta", "pil_resolved_executions")
    ),
)


class PostgresResolvedExecutionArchive:
    def __init__(self, prefix: PostgresPlannedExecutionArchive, codec: SemanticCodec) -> None:
        self.prefix = prefix
        self.codec = codec

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self.prefix._check(conn)
        if conn.execute("SELECT singleton,version FROM pil_resolved_execution_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise ArchiveIntegrityError("unsupported resolved execution archive capability")
        conn.execute(
            "SELECT sequence,scope,execution_digest,retained_receipt_digest,snapshot_id,prefix_execution_digest,retained_prefix_receipt_digest,payload,payload_sha256 FROM pil_resolved_executions LIMIT 0"
        )

    def initialize(self) -> None:
        with self.prefix.source._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725126)")
            self.prefix._check(conn)
            row = conn.execute(
                "SELECT to_regclass('pil_resolved_execution_meta') AS name"
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("resolved archive initialization produced no metadata")
            if row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)

    def check_ready(self) -> None:
        with self.prefix.source._connection() as conn:
            self._check(conn)

    def append(
        self, completed: CompletedResolvedPrefixSnapshot, content: bytes
    ) -> ArchivedResolvedPrefix:
        if type(completed) is not CompletedResolvedPrefixSnapshot:
            raise ArchiveContractError("resolved archive requires a complete typed computation")
        artifact = completed.prefix.snapshot.artifact
        if (
            type(content) is not bytes
            or len(content) != artifact.byte_length
            or sha256(content).hexdigest() != artifact.content_hash
        ):
            raise ArchiveContractError("resolved archive requires exact captured source bytes")
        payload = self.codec.dumps(completed)
        with self.prefix.source._connection() as conn:
            self._check(conn)
            retained_prefix = self.prefix._append_in_transaction(conn, completed.prefix, content)
            conn.execute("LOCK TABLE pil_resolved_executions IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT execution_digest FROM pil_resolved_executions WHERE scope=%s AND execution_digest=%s",
                (_scope(completed.scope), completed.execution_digest),
            ).fetchone()
            if row is not None:
                retained = self._load(conn, completed.scope, completed.execution_digest)
                if not same_resolved_computation(completed, retained.completed):
                    raise ArchiveConflictError(
                        "resolved execution identity conflicts with retained computation"
                    )
                return retained
            row = conn.execute(
                "INSERT INTO pil_resolved_executions(scope,execution_digest,retained_receipt_digest,snapshot_id,prefix_execution_digest,retained_prefix_receipt_digest,payload,payload_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING sequence",
                (
                    _scope(completed.scope),
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    completed.prefix.snapshot.snapshot_id,
                    completed.prefix.execution_digest,
                    retained_prefix.receipt.retained_receipt_digest,
                    payload,
                    sha256(payload.encode()).hexdigest(),
                ),
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("resolved execution insert produced no receipt")
            return ArchivedResolvedPrefix(
                completed,
                ResolvedExecutionArchiveReceipt(
                    row["sequence"],
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    retained_prefix.receipt,
                ),
                retained_prefix,
            )

    def _load(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, execution_digest: str
    ) -> ArchivedResolvedPrefix:
        row = conn.execute(
            "SELECT * FROM pil_resolved_executions WHERE scope=%s AND execution_digest=%s",
            (_scope(scope), execution_digest),
        ).fetchone()
        if row is None:
            raise ArchiveNotFoundError("resolved execution not found in requested scope")
        try:
            if sha256(row["payload"].encode()).hexdigest() != row["payload_sha256"]:
                raise ArchiveIntegrityError("resolved execution payload checksum mismatch")
            completed = self.codec.loads(row["payload"])
            if (
                type(completed) is not CompletedResolvedPrefixSnapshot
                or canonical(completed.scope) != canonical(scope)
                or completed.execution_digest != execution_digest
            ):
                raise ArchiveIntegrityError("resolved execution identity or scope mismatch")
            if (
                completed.execution.receipt_digest != row["retained_receipt_digest"]
                or completed.prefix.execution_digest != row["prefix_execution_digest"]
                or completed.prefix.snapshot.snapshot_id != row["snapshot_id"]
            ):
                raise ArchiveIntegrityError("resolved execution receipt or prefix binding mismatch")
            retained_prefix = self.prefix._load(conn, scope, row["prefix_execution_digest"])
            if (
                retained_prefix.receipt.retained_receipt_digest
                != row["retained_prefix_receipt_digest"]
            ):
                raise ArchiveIntegrityError("resolved execution retained prefix receipt mismatch")
            self.prefix.source._content(conn, completed.prefix.snapshot)
            return ArchivedResolvedPrefix(
                completed,
                ResolvedExecutionArchiveReceipt(
                    row["sequence"],
                    execution_digest,
                    row["retained_receipt_digest"],
                    retained_prefix.receipt,
                ),
                retained_prefix,
            )
        except SemanticContractError:
            raise ArchiveIntegrityError("retained resolved execution evidence is invalid") from None

    def load(self, scope: StateScope, execution_digest: str) -> ArchivedResolvedPrefix:
        scope_contract(scope)
        execution_key(execution_digest)
        with self.prefix.source._connection() as conn:
            self._check(conn)
            return self._load(conn, scope, execution_digest)

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ResolvedExecutionHistoryPage:
        history_bounds(scope, limit, after_sequence)
        with self.prefix.source._connection() as conn:
            self._check(conn)
            rows = conn.execute(
                "SELECT execution_digest FROM pil_resolved_executions WHERE scope=%s AND sequence>%s ORDER BY sequence LIMIT %s",
                (_scope(scope), after_sequence, limit + 1),
            ).fetchall()
            receipts = tuple(
                self._load(conn, scope, row["execution_digest"]).receipt for row in rows[:limit]
            )
            more = len(rows) > limit
            return ResolvedExecutionHistoryPage(
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
        with self.prefix.source._connection() as conn:
            self._check(conn)
            retained = self._load(conn, scope, execution_digest)
            return self.prefix.source._content(conn, retained.completed.prefix.snapshot)
