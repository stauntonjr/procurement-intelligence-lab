"""Additive immutable dependency registrations with exact archive membership."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from typing import Any, LiteralString, cast

import psycopg
from psycopg.rows import dict_row

from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.dependencies import (
    DependencyManifest,
    DependencySnapshot,
    aware,
    text,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
    DependencyConflictError,
    DependencyContractError,
    DependencyIntegrityError,
    DependencyNotFoundError,
    DependencyUnavailableError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.assertion_archive import AssertionArchive

_SCHEMA = (
    "CREATE TABLE pil_dependency_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_dependency_meta VALUES (1,1)",
    "CREATE TABLE pil_dependency_snapshots (scope TEXT NOT NULL, snapshot_id TEXT NOT NULL, command_hash TEXT NOT NULL, content_digest TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, PRIMARY KEY(scope,snapshot_id))",
    "CREATE TABLE pil_dependency_roots (scope TEXT NOT NULL, dependency_snapshot_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL, assertion_id TEXT NOT NULL, PRIMARY KEY(scope,dependency_snapshot_id,assertion_id), FOREIGN KEY(scope,dependency_snapshot_id) REFERENCES pil_dependency_snapshots(scope,snapshot_id), FOREIGN KEY(scope,source_snapshot_id,assertion_id) REFERENCES pil_archive_members(scope,snapshot_id,assertion_id))",
    *(
        f"CREATE TRIGGER pil_dependency_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in ("pil_dependency_meta", "pil_dependency_snapshots", "pil_dependency_roots")
    ),
)


def _scope(scope: StateScope) -> str:
    return stable_id("archive-scope-v1", scope)


def _checksum(raw: str) -> str:
    return sha256(raw.encode()).hexdigest()


class PostgresDependencyStore:
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
            raise DependencyUnavailableError(
                "dependency backend is unavailable or not explicitly initialized"
            ) from None

    def _check(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        for table in ("pil_dependency_meta", "pil_archive_meta"):
            if conn.execute(f"SELECT singleton,version FROM {table}").fetchall() != [
                {"singleton": 1, "version": 1}
            ]:
                raise DependencyIntegrityError("unsupported dependency/archive schema")

    def initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(640725126)")
            if conn.execute("SELECT singleton,version FROM pil_archive_meta").fetchall() != [
                {"singleton": 1, "version": 1}
            ]:
                raise DependencyIntegrityError("dependency storage requires archive schema1")
            row = conn.execute("SELECT to_regclass('pil_dependency_meta') AS name").fetchone()
            if row is not None and row["name"] is None:
                for statement in _SCHEMA:
                    conn.execute(cast(LiteralString, statement))
            self._check(conn)
            conn.execute(
                "SELECT s.scope,s.snapshot_id,s.command_hash,s.content_digest,s.payload,s.payload_sha256,r.source_snapshot_id,r.assertion_id FROM pil_dependency_snapshots s LEFT JOIN pil_dependency_roots r ON (s.scope=r.scope AND s.snapshot_id=r.dependency_snapshot_id) LIMIT 0"
            )

    def _sources(self, snapshot: DependencySnapshot, *, retained: bool) -> None:
        cache: dict[str, DocumentSnapshot] = {}
        try:
            for root in snapshot.manifest.roots:
                if root.snapshot_id not in cache:
                    cache[root.snapshot_id] = self.archive.load(
                        snapshot.manifest.scope, root.snapshot_id
                    )[1]
                source = cache[root.snapshot_id]
                if root.assertion_id not in {a.assertion_id for a in source.assertions}:
                    raise ArchiveNotFoundError("dependency source assertion not found")
                if source.origin.recorded_at > snapshot.recorded_at:
                    if retained:
                        raise DependencyIntegrityError("retained dependency predates source")
                    raise DependencyContractError(
                        "dependency recording cannot precede source recording"
                    )
        except ArchiveUnavailableError:
            raise DependencyUnavailableError("dependency source backend is unavailable") from None
        except (ArchiveIntegrityError, ArchiveNotFoundError):
            if retained:
                raise DependencyIntegrityError(
                    "retained dependency source is missing or corrupt"
                ) from None
            raise DependencyNotFoundError(
                "dependency requires exact scoped archive roots"
            ) from None

    def _get(
        self, conn: psycopg.Connection[dict[str, Any]], scope: StateScope, snapshot_id: str
    ) -> DependencySnapshot:
        row = conn.execute(
            "SELECT * FROM pil_dependency_snapshots WHERE scope=%s AND snapshot_id=%s",
            (_scope(scope), snapshot_id),
        ).fetchone()
        if row is None:
            raise DependencyNotFoundError("dependency snapshot not found in requested scope")
        if _checksum(row["payload"]) != row["payload_sha256"]:
            raise DependencyIntegrityError("dependency payload checksum mismatch")
        try:
            result = self.codec.loads(row["payload"])
        except SemanticContractError:
            raise DependencyIntegrityError("retained dependency graph is invalid") from None
        if (
            type(result) is not DependencySnapshot
            or result.manifest.scope != scope
            or result.snapshot_id != snapshot_id
            or result.digest != row["content_digest"]
            or _checksum(self.codec.dumps((result.manifest, result.recorder_id)))
            != row["command_hash"]
        ):
            raise DependencyIntegrityError("dependency identity/content digest mismatch")
        rows = conn.execute(
            "SELECT source_snapshot_id,assertion_id FROM pil_dependency_roots WHERE scope=%s AND dependency_snapshot_id=%s",
            (_scope(scope), snapshot_id),
        ).fetchall()
        if {(r["source_snapshot_id"], r["assertion_id"]) for r in rows} != {
            (r.snapshot_id, r.assertion_id) for r in result.manifest.roots
        }:
            raise DependencyIntegrityError(
                "dependency root membership differs from retained manifest"
            )
        self._sources(result, retained=True)
        return result

    def append(
        self, manifest: DependencyManifest, recorder_id: str, recorded_at: datetime
    ) -> DependencySnapshot:
        aware(recorded_at)
        text(recorder_id)
        command_hash = _checksum(self.codec.dumps((manifest, recorder_id)))
        snapshot_id = stable_id("dependency-snapshot-v1", manifest.scope, manifest.request_id)
        with self._connection() as conn:
            self._check(conn)
            conn.execute("LOCK TABLE pil_dependency_snapshots IN SHARE ROW EXCLUSIVE MODE")
            row = conn.execute(
                "SELECT command_hash FROM pil_dependency_snapshots WHERE scope=%s AND snapshot_id=%s",
                (_scope(manifest.scope), snapshot_id),
            ).fetchone()
            if row is not None:
                if row["command_hash"] != command_hash:
                    raise DependencyConflictError(
                        "dependency request identity conflicts with retained registration"
                    )
                return self._get(conn, manifest.scope, snapshot_id)
            snapshot = DependencySnapshot(manifest, recorder_id, recorded_at)
            self._sources(snapshot, retained=False)
            payload = self.codec.dumps(snapshot)
            conn.execute(
                "INSERT INTO pil_dependency_snapshots VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    _scope(manifest.scope),
                    snapshot_id,
                    command_hash,
                    snapshot.digest,
                    payload,
                    _checksum(payload),
                ),
            )
            for root in manifest.roots:
                conn.execute(
                    "INSERT INTO pil_dependency_roots VALUES (%s,%s,%s,%s)",
                    (_scope(manifest.scope), snapshot_id, root.snapshot_id, root.assertion_id),
                )
            return snapshot

    def get(self, scope: StateScope, snapshot_id: str) -> DependencySnapshot:
        text(snapshot_id)
        with self._connection() as conn:
            self._check(conn)
            return self._get(conn, scope, snapshot_id)
