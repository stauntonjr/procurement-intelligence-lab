"""Atomic publication over already-retained six-stage producers; no implicit import."""

# pyright: reportPrivateUsage=false
from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg

from procurement_intelligence_lab.adapters.postgres_archive import _scope
from procurement_intelligence_lab.adapters.postgres_resolved_execution_archive import (
    PostgresResolvedExecutionArchive,
)
from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.execution.archive import (
    execution_key,
    history_bounds,
    scope_contract,
)
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    ArchivedReconciliation,
    CompletedReconciliationSnapshot,
    ReconciliationArchiveReceipt,
    ReconciliationHistoryPage,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    same_reconciliation_computation,
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
    "CREATE TABLE pil_reconciliation_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_reconciliation_meta VALUES (1,1)",
    "CREATE TABLE pil_reconciliations (sequence BIGSERIAL PRIMARY KEY,scope TEXT NOT NULL,execution_digest TEXT NOT NULL,retained_receipt_digest TEXT NOT NULL,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL,UNIQUE(scope,execution_digest))",
    "CREATE TABLE pil_reconciliation_producers (scope TEXT NOT NULL,execution_digest TEXT NOT NULL,position INTEGER NOT NULL CHECK(position>=0 AND position<8),producer_execution_digest TEXT NOT NULL,producer_sequence BIGINT NOT NULL,retained_receipt_digest TEXT NOT NULL,PRIMARY KEY(scope,execution_digest,position),UNIQUE(scope,execution_digest,producer_execution_digest),FOREIGN KEY(scope,execution_digest) REFERENCES pil_reconciliations(scope,execution_digest),FOREIGN KEY(scope,producer_execution_digest) REFERENCES pil_resolved_executions(scope,execution_digest))",
    *(
        f"CREATE TRIGGER pil_reconciliation_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in (
            "pil_reconciliation_meta",
            "pil_reconciliations",
            "pil_reconciliation_producers",
        )
    ),
)


class PostgresReconciliationArchive:
    def __init__(self, resolved: PostgresResolvedExecutionArchive, codec: SemanticCodec) -> None:
        self.resolved = resolved
        self.codec = codec

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self.resolved._check(conn)
        if conn.execute("SELECT singleton,version FROM pil_reconciliation_meta").fetchall() != [
            {"singleton": 1, "version": 1}
        ]:
            raise ArchiveIntegrityError("unsupported retained reconciliation capability")
        conn.execute(
            "SELECT sequence,scope,execution_digest,retained_receipt_digest,payload,payload_sha256 FROM pil_reconciliations LIMIT 0"
        )
        conn.execute(
            "SELECT scope,execution_digest,position,producer_execution_digest,producer_sequence,retained_receipt_digest FROM pil_reconciliation_producers LIMIT 0"
        )

    def initialize(self) -> None:
        with self.resolved.prefix.source._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725127)")
            self.resolved._check(conn)
            row = conn.execute("SELECT to_regclass('pil_reconciliation_meta') AS name").fetchone()
            if row is None:
                raise ArchiveIntegrityError("reconciliation initialization produced no metadata")
            if row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)

    def check_ready(self) -> None:
        with self.resolved.prefix.source._connection() as conn:
            self._check(conn)

    def _append_links(
        self, conn: psycopg.Connection[dict[str, Any]], completed: CompletedReconciliationSnapshot
    ) -> None:
        for position, p in enumerate(completed.execution.output.inputs.recorded_producers):
            conn.execute(
                "INSERT INTO pil_reconciliation_producers(scope,execution_digest,position,producer_execution_digest,producer_sequence,retained_receipt_digest) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    _scope(completed.scope),
                    completed.execution_digest,
                    position,
                    p.receipt.execution_digest,
                    p.receipt.sequence,
                    p.receipt.retained_receipt_digest,
                ),
            )

    def append(self, completed: CompletedReconciliationSnapshot) -> ArchivedReconciliation:
        if type(completed) is not CompletedReconciliationSnapshot:
            raise ArchiveContractError(
                "reconciliation archive requires a typed completed operation"
            )
        payload = self.codec.dumps(completed)
        with self.resolved.prefix.source._connection() as conn:
            self._check(conn)
            for p in completed.execution.output.inputs.recorded_producers:
                row = conn.execute(
                    "SELECT sequence FROM pil_resolved_executions WHERE scope=%s AND execution_digest=%s FOR SHARE",
                    (_scope(completed.scope), p.completed.execution_digest),
                ).fetchone()
                if row is None:
                    raise ArchiveNotFoundError(
                        "selected producer is not retained in requested scope"
                    )
                stored = self.resolved._load(conn, completed.scope, p.completed.execution_digest)
                if canonical(stored) != canonical(p):
                    raise ArchiveConflictError(
                        "selected producer audit receipt conflicts with retained evidence"
                    )
            conn.execute("LOCK TABLE pil_reconciliations IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT execution_digest FROM pil_reconciliations WHERE scope=%s AND execution_digest=%s",
                (_scope(completed.scope), completed.execution_digest),
            ).fetchone()
            if row is not None:
                retained = self._load(conn, completed.scope, completed.execution_digest)
                if not same_reconciliation_computation(
                    completed.execution, retained.completed.execution
                ):
                    raise ArchiveConflictError(
                        "reconciliation identity conflicts with retained computation"
                    )
                return retained
            row = conn.execute(
                "INSERT INTO pil_reconciliations(scope,execution_digest,retained_receipt_digest,payload,payload_sha256) VALUES (%s,%s,%s,%s,%s) RETURNING sequence",
                (
                    _scope(completed.scope),
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    payload,
                    sha256(payload.encode()).hexdigest(),
                ),
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("reconciliation insert produced no receipt")
            self._append_links(conn, completed)
            retained = ArchivedReconciliation(
                completed,
                ReconciliationArchiveReceipt(
                    completed.scope,
                    row["sequence"],
                    completed.execution_digest,
                    completed.execution.receipt_digest,
                    tuple(p.receipt for p in completed.execution.output.inputs.recorded_producers),
                ),
            )
            self.codec.dumps(retained)
            return retained

    def _load(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, execution_digest: str
    ) -> ArchivedReconciliation:
        row = conn.execute(
            "SELECT * FROM pil_reconciliations WHERE scope=%s AND execution_digest=%s",
            (_scope(scope), execution_digest),
        ).fetchone()
        if row is None:
            raise ArchiveNotFoundError("reconciliation not found in requested scope")
        try:
            if sha256(row["payload"].encode()).hexdigest() != row["payload_sha256"]:
                raise ArchiveIntegrityError("reconciliation payload checksum mismatch")
            completed = self.codec.loads(row["payload"])
            if (
                type(completed) is not CompletedReconciliationSnapshot
                or canonical(completed.scope) != canonical(scope)
                or completed.execution_digest != execution_digest
                or completed.execution.receipt_digest != row["retained_receipt_digest"]
            ):
                raise ArchiveIntegrityError("reconciliation retained identity or scope mismatch")
            links = conn.execute(
                "SELECT * FROM pil_reconciliation_producers WHERE scope=%s AND execution_digest=%s ORDER BY position",
                (_scope(scope), execution_digest),
            ).fetchall()
            ps = completed.execution.output.inputs.recorded_producers
            if len(links) != len(ps):
                raise ArchiveIntegrityError("reconciliation producer link set is incomplete")
            for i, (link, p) in enumerate(zip(links, ps, strict=True)):
                if (
                    link["position"],
                    link["producer_execution_digest"],
                    link["producer_sequence"],
                    link["retained_receipt_digest"],
                ) != (
                    i,
                    p.receipt.execution_digest,
                    p.receipt.sequence,
                    p.receipt.retained_receipt_digest,
                ):
                    raise ArchiveIntegrityError("reconciliation producer receipt join mismatch")
                stored = self.resolved._load(conn, scope, link["producer_execution_digest"])
                if canonical(stored) != canonical(p):
                    raise ArchiveIntegrityError("reconciliation recorded producer graph mismatch")
            retained = ArchivedReconciliation(
                completed,
                ReconciliationArchiveReceipt(
                    scope,
                    row["sequence"],
                    execution_digest,
                    row["retained_receipt_digest"],
                    tuple(p.receipt for p in ps),
                ),
            )
            self.codec.dumps(retained)
            return retained
        except (SemanticContractError, ValueError, TypeError, KeyError, AttributeError):
            raise ArchiveIntegrityError(
                "retained reconciliation evidence or producer joins are invalid"
            ) from None

    def load(self, scope: StateScope, execution_digest: str) -> ArchivedReconciliation:
        scope_contract(scope)
        execution_key(execution_digest)
        with self.resolved.prefix.source._connection() as conn:
            self._check(conn)
            return self._load(conn, scope, execution_digest)

    def history(
        self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0
    ) -> ReconciliationHistoryPage:
        history_bounds(scope, limit, after_sequence)
        with self.resolved.prefix.source._connection() as conn:
            self._check(conn)
            rows = conn.execute(
                "SELECT execution_digest FROM pil_reconciliations WHERE scope=%s AND sequence>%s ORDER BY sequence LIMIT %s",
                (_scope(scope), after_sequence, limit + 1),
            ).fetchall()
            receipts = tuple(
                self._load(conn, scope, r["execution_digest"]).receipt for r in rows[:limit]
            )
            more = len(rows) > limit
            return ReconciliationHistoryPage(
                scope,
                after_sequence,
                limit,
                receipts,
                more,
                receipts[-1].sequence if more else None,
            )
