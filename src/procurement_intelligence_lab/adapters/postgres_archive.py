"""Postgres atomic append-only source archive; no domain policy or implicit schema migration."""

from collections.abc import Generator
from contextlib import contextmanager
from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg
from psycopg.rows import dict_row

from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt, DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope

_SCHEMA = (
    "CREATE TABLE pil_archive_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_archive_meta VALUES (1,1)",
    "CREATE TABLE pil_archive_content (content_hash TEXT PRIMARY KEY, byte_length BIGINT NOT NULL CHECK(byte_length>=0), content BYTEA NOT NULL)",
    "CREATE TABLE pil_archive_batches (sequence BIGSERIAL PRIMARY KEY, scope TEXT NOT NULL, snapshot_id TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, content_hash TEXT NOT NULL REFERENCES pil_archive_content(content_hash), UNIQUE(scope,snapshot_id))",
    "CREATE TABLE pil_archive_claims (scope TEXT NOT NULL, assertion_id TEXT NOT NULL, node_digest TEXT NOT NULL, PRIMARY KEY(scope,assertion_id))",
    "CREATE TABLE pil_archive_members (scope TEXT NOT NULL, snapshot_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal>=0), assertion_id TEXT NOT NULL, PRIMARY KEY(scope,snapshot_id,ordinal), UNIQUE(scope,snapshot_id,assertion_id), FOREIGN KEY(scope,snapshot_id) REFERENCES pil_archive_batches(scope,snapshot_id), FOREIGN KEY(scope,assertion_id) REFERENCES pil_archive_claims(scope,assertion_id))",
    "CREATE FUNCTION pil_archive_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'archive records are immutable'; END $$",
    *(
        f"CREATE TRIGGER pil_archive_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in (
            "pil_archive_content",
            "pil_archive_batches",
            "pil_archive_claims",
            "pil_archive_members",
            "pil_archive_meta",
        )
    ),
)


def _scope(scope: StateScope) -> str:
    return stable_id("archive-scope-v1", scope)


def _receipt(sequence: int, snapshot: DocumentSnapshot) -> ArchiveReceipt:
    artifact = snapshot.artifact
    return ArchiveReceipt(
        sequence,
        snapshot.snapshot_id,
        artifact.source.scope,
        artifact.artifact_id,
        artifact.content_hash,
        len(snapshot.assertions),
        snapshot.origin.recorded_at,
    )


class PostgresAssertionArchive:
    def __init__(self, dsn: str, codec: SemanticCodec) -> None:
        if not dsn.strip():
            raise ArchiveContractError("archive connection configuration is required")
        self._dsn = dsn
        self.codec = codec

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
            raise ArchiveUnavailableError(
                "archive backend is unavailable or schema is not initialized"
            ) from None

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        rows = conn.execute("SELECT singleton,version FROM pil_archive_meta").fetchall()
        if rows != [{"singleton": 1, "version": 1}]:
            raise ArchiveIntegrityError("unsupported archive schema")

    def initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725124)")
            metadata = conn.execute(
                "SELECT to_regclass('pil_archive_meta') AS table_name"
            ).fetchone()
            if metadata is None:
                raise ArchiveIntegrityError("archive initialization produced no metadata")
            if metadata["table_name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)
            # Admit the expected column set even on an already initialized schema.
            conn.execute(
                "SELECT b.sequence,b.scope,b.snapshot_id,b.payload,b.payload_sha256,b.content_hash,c.byte_length,c.content,m.ordinal,m.assertion_id,a.node_digest FROM pil_archive_batches b LEFT JOIN pil_archive_content c USING(content_hash) LEFT JOIN pil_archive_members m USING(scope,snapshot_id) LEFT JOIN pil_archive_claims a USING(scope,assertion_id) LIMIT 0"
            )

    def append(self, snapshot: DocumentSnapshot, content: bytes) -> ArchiveReceipt:
        if (
            type(content) is not bytes
            or len(content) != snapshot.artifact.byte_length
            or sha256(content).hexdigest() != snapshot.artifact.content_hash
        ):
            raise ArchiveContractError("archive requires the exact captured bytes and metadata")
        payload = self.codec.dumps(snapshot)
        checksum = sha256(payload.encode()).hexdigest()
        scope = _scope(snapshot.artifact.source.scope)
        with self._connection() as conn:
            self._check(conn)
            conn.execute("LOCK TABLE pil_archive_batches IN SHARE ROW EXCLUSIVE MODE")
            existing = conn.execute(
                "SELECT sequence,payload,payload_sha256 FROM pil_archive_batches WHERE scope=%s AND snapshot_id=%s",
                (scope, snapshot.snapshot_id),
            ).fetchone()
            if existing is not None:
                if existing["payload"] != payload or existing["payload_sha256"] != checksum:
                    raise ArchiveConflictError("snapshot identity conflicts with retained content")
                receipt, retained = self._load(
                    conn, snapshot.artifact.source.scope, snapshot.snapshot_id
                )
                if retained != snapshot:
                    raise ArchiveConflictError("snapshot replay differs from retained records")
                return receipt
            conn.execute(
                "INSERT INTO pil_archive_content VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (snapshot.artifact.content_hash, len(content), content),
            )
            stored = conn.execute(
                "SELECT byte_length,content FROM pil_archive_content WHERE content_hash=%s",
                (snapshot.artifact.content_hash,),
            ).fetchone()
            if (
                stored is None
                or stored["byte_length"] != len(content)
                or stored["content"] != content
            ):
                raise ArchiveIntegrityError(
                    "captured byte identity conflicts with retained content"
                )
            row = conn.execute(
                "INSERT INTO pil_archive_batches(scope,snapshot_id,payload,payload_sha256,content_hash) VALUES (%s,%s,%s,%s,%s) RETURNING sequence",
                (scope, snapshot.snapshot_id, payload, checksum, snapshot.artifact.content_hash),
            ).fetchone()
            if row is None:
                raise ArchiveIntegrityError("archive insert produced no receipt")
            for ordinal, claim in enumerate(snapshot.assertions):
                node = self.codec.node_digest(claim)
                conn.execute(
                    "INSERT INTO pil_archive_claims VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (scope, claim.assertion_id, node),
                )
                stored_claim = conn.execute(
                    "SELECT node_digest FROM pil_archive_claims WHERE scope=%s AND assertion_id=%s",
                    (scope, claim.assertion_id),
                ).fetchone()
                if stored_claim is None or stored_claim["node_digest"] != node:
                    raise ArchiveConflictError("assertion identity conflicts with retained content")
                conn.execute(
                    "INSERT INTO pil_archive_members VALUES (%s,%s,%s,%s)",
                    (scope, snapshot.snapshot_id, ordinal, claim.assertion_id),
                )
            return _receipt(row["sequence"], snapshot)

    def _load(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, snapshot_id: str
    ) -> tuple[ArchiveReceipt, DocumentSnapshot]:
        row = conn.execute(
            "SELECT * FROM pil_archive_batches WHERE scope=%s AND snapshot_id=%s",
            (_scope(scope), snapshot_id),
        ).fetchone()
        if row is None:
            raise ArchiveNotFoundError("archive snapshot not found in requested scope")
        if sha256(row["payload"].encode()).hexdigest() != row["payload_sha256"]:
            raise ArchiveIntegrityError("archive payload checksum mismatch")
        snapshot = self.codec.loads(row["payload"])
        if (
            type(snapshot) is not DocumentSnapshot
            or snapshot.snapshot_id != snapshot_id
            or snapshot.artifact.source.scope != scope
            or snapshot.artifact.content_hash != row["content_hash"]
        ):
            raise ArchiveIntegrityError("archive snapshot identity or scope mismatch")
        members = conn.execute(
            "SELECT m.ordinal,m.assertion_id,a.node_digest FROM pil_archive_members m JOIN pil_archive_claims a USING(scope,assertion_id) WHERE m.scope=%s AND m.snapshot_id=%s ORDER BY ordinal",
            (_scope(scope), snapshot_id),
        ).fetchall()
        expected = [
            {"ordinal": i, "assertion_id": a.assertion_id, "node_digest": self.codec.node_digest(a)}
            for i, a in enumerate(snapshot.assertions)
        ]
        if members != expected:
            raise ArchiveIntegrityError("archive claim membership is incomplete or corrupt")
        self._content(conn, snapshot)
        return _receipt(row["sequence"], snapshot), snapshot

    def _content(
        self, conn: psycopg.Connection[dict[str, Any]], snapshot: DocumentSnapshot
    ) -> bytes:
        row = conn.execute(
            "SELECT byte_length,content FROM pil_archive_content WHERE content_hash=%s",
            (snapshot.artifact.content_hash,),
        ).fetchone()
        if row is None:
            raise ArchiveIntegrityError("captured content is missing")
        content = row["content"]
        if (
            type(content) is not bytes
            or len(content) != row["byte_length"]
            or len(content) != snapshot.artifact.byte_length
            or sha256(content).hexdigest() != snapshot.artifact.content_hash
        ):
            raise ArchiveIntegrityError("captured content length or hash mismatch")
        return content

    def load(self, scope: StateScope, snapshot_id: str) -> tuple[ArchiveReceipt, DocumentSnapshot]:
        with self._connection() as conn:
            self._check(conn)
            return self._load(conn, scope, snapshot_id)

    def history(self, scope: StateScope) -> tuple[ArchiveReceipt, ...]:
        with self._connection() as conn:
            self._check(conn)
            rows = conn.execute(
                "SELECT snapshot_id FROM pil_archive_batches WHERE scope=%s ORDER BY sequence",
                (_scope(scope),),
            ).fetchall()
            return tuple(self._load(conn, scope, row["snapshot_id"])[0] for row in rows)

    def content(self, scope: StateScope, snapshot_id: str) -> bytes:
        with self._connection() as conn:
            self._check(conn)
            _, snapshot = self._load(conn, scope, snapshot_id)
            return self._content(conn, snapshot)
