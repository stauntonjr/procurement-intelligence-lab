from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from typing import LiteralString, cast

import psycopg
import pytest
from psycopg import sql

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
)
from tests.planned_execution_archive_fixtures import executed, parameters

pytestmark = pytest.mark.contract


def setup(dsn):
    source = bootstrap.build_assertion_archive(dsn)
    source.initialize()
    assert hasattr(bootstrap, "build_planned_execution_archive"), "planned archive adapter absent"
    archive = bootstrap.build_planned_execution_archive(dsn)
    archive.initialize()
    return source, archive


def completed(tmp_path, name="source.xlsx"):
    r, content = executed(tmp_path / name)
    return CompletedPrefixSnapshot.from_execution(r, parameters()), content


def test_restart_first_retention_exact_bytes_and_legacy_reader(archive_dsn, tmp_path):
    source, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    retained = archive.append(first, content)
    later = replace(
        first,
        execution=replace(
            first.execution, completed_at=first.execution.completed_at + timedelta(seconds=2)
        ),
    )
    assert canonical(archive.append(later, content)) == canonical(retained)
    fresh = bootstrap.build_planned_execution_archive(archive_dsn)
    assert canonical(fresh.load(first.scope, first.execution_digest)) == canonical(retained)
    assert fresh.content(first.scope, first.execution_digest) == content
    receipt, snapshot = source.load(first.scope, first.snapshot.snapshot_id)
    assert receipt == retained.receipt.source_receipt
    assert canonical(snapshot) == canonical(first.snapshot)
    assert source.content(first.scope, snapshot.snapshot_id) == content
    assert source.history(first.scope) == (receipt,)
    for invalid in (b"", content + b"x", bytearray(content)):
        with pytest.raises(ArchiveContractError):
            fresh.append(later, invalid)
    foreign = replace(first.scope, version="foreign")
    assert fresh.history(foreign).receipts == ()
    for read in (fresh.load, fresh.content):
        with pytest.raises(ArchiveNotFoundError):
            read(foreign, first.execution_digest)


def test_concurrent_sixteen_appends_converge(archive_dsn, tmp_path):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: archive.append(first, content), range(16)))
    assert all(canonical(x) == canonical(results[0]) for x in results)
    with psycopg.connect(archive_dsn) as c:
        for table, count in [
            ("pil_planned_executions", 1),
            ("pil_archive_batches", 1),
            ("pil_archive_content", 1),
            ("pil_archive_members", 4),
            ("pil_archive_claims", 4),
        ]:
            assert c.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (count,)


def test_source_and_binding_roll_back_together(archive_dsn, tmp_path):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    with psycopg.connect(archive_dsn) as c:
        c.execute(
            "CREATE FUNCTION fail_binding() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test'; END $$"
        )
        c.execute(
            "CREATE TRIGGER fail_binding BEFORE INSERT ON pil_planned_executions FOR EACH ROW EXECUTE FUNCTION fail_binding()"
        )
    with pytest.raises(ArchiveUnavailableError):
        archive.append(first, content)
    with psycopg.connect(archive_dsn) as c:
        for table in (
            "pil_archive_content",
            "pil_archive_batches",
            "pil_archive_claims",
            "pil_archive_members",
            "pil_planned_executions",
        ):
            assert c.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)


def test_lost_acknowledgement_does_not_imply_rollback(archive_dsn, tmp_path, monkeypatch):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    original = archive.source._connection

    @contextmanager
    def lose_ack():
        with original() as c:
            yield c
        raise ArchiveUnavailableError("archive acknowledgement unavailable")

    monkeypatch.setattr(archive.source, "_connection", lose_ack)
    with pytest.raises(ArchiveUnavailableError):
        archive.append(first, content)
    fresh = bootstrap.build_planned_execution_archive(archive_dsn)
    retained = fresh.load(first.scope, first.execution_digest)
    assert canonical(fresh.append(first, content)) == canonical(retained)
    assert len(fresh.history(first.scope).receipts) == 1


def test_digest_collision_cannot_hide_changed_snapshot_policy(archive_dsn, tmp_path, monkeypatch):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    retained = archive.append(first, content)
    # Parameters are part of the canonical snapshot even though old snapshot_id excludes them.
    changed = replace(
        first,
        snapshot=replace(first.snapshot, normalization_policy_parameters=(("changed", "value"),)),
    )
    assert changed.execution_digest == first.execution_digest
    with pytest.raises(ArchiveConflictError):
        archive.append(changed, content)
    assert canonical(archive.load(first.scope, first.execution_digest)) == canonical(retained)
    # Force a computation hash collision in tests only; compare full computation bytes.
    other, content2 = completed(tmp_path, "other.xlsx")
    key = first.execution_digest
    monkeypatch.setattr(type(first.execution), "execution_digest", property(lambda _: key))
    with pytest.raises(ArchiveConflictError):
        archive.append(other, content2)


def test_explicit_capability_and_supported_base(archive_dsn, tmp_path):
    assert hasattr(bootstrap, "build_planned_execution_archive")
    archive = bootstrap.build_planned_execution_archive(archive_dsn)
    with pytest.raises(ArchiveUnavailableError):
        archive.initialize()
    with psycopg.connect(archive_dsn) as c:
        assert c.execute("SELECT to_regclass('pil_planned_execution_meta')").fetchone() == (None,)
    bootstrap.build_assertion_archive(archive_dsn).initialize()
    with pytest.raises(ArchiveUnavailableError):
        archive.check_ready()
    archive.initialize()
    archive.initialize()
    archive.check_ready()


@pytest.mark.parametrize(
    "limit,after", [(0, 0), (201, 0), (True, 0), (1.5, 0), (1, -1), (1, True), (1, 0.5)]
)
def test_history_rejects_bad_bounds_before_storage(archive_dsn, tmp_path, limit, after):
    _, archive = setup(archive_dsn)
    first, _ = completed(tmp_path)
    with pytest.raises(ArchiveContractError):
        archive.history(first.scope, limit=limit, after_sequence=after)


def test_history_pages_use_actual_extra_row_and_exclusive_cursor(archive_dsn, tmp_path):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    a = archive.append(first, content).receipt
    for limit in (1, 100, 200):
        page = archive.history(first.scope, limit=limit)
        assert not page.has_more and page.next_after_sequence is None
    other, content = completed(tmp_path, "second.xlsx")
    b = archive.append(other, content).receipt
    page = archive.history(first.scope, limit=1)
    assert page.receipts == (a,) and page.has_more and page.next_after_sequence == a.sequence
    page = archive.history(first.scope, limit=1, after_sequence=a.sequence)
    assert page.receipts == (b,) and not page.has_more and page.next_after_sequence is None
    assert archive.history(first.scope, after_sequence=b.sequence).receipts == ()


@pytest.mark.parametrize("table", ["pil_planned_execution_meta", "pil_planned_executions"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
def test_new_sql_records_are_immutable(archive_dsn, table, operation):
    setup(archive_dsn)
    statement = (
        f"UPDATE {table} SET " + ("version=1" if table.endswith("meta") else "scope=scope")
        if operation == "UPDATE"
        else f"{operation} " + ("FROM " if operation == "DELETE" else "") + table
    )
    with psycopg.connect(archive_dsn) as c, pytest.raises(psycopg.Error):
        c.execute(cast(LiteralString, statement))


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE pil_planned_execution_meta SET version=99",
        "UPDATE pil_planned_executions SET payload_sha256='bad'",
        "UPDATE pil_planned_executions SET payload='{}'",
        "UPDATE pil_planned_executions SET retained_receipt_digest=repeat('a',64)",
        "UPDATE pil_planned_executions SET execution_digest=repeat('b',64)",
        "UPDATE pil_archive_batches SET payload_sha256='bad'",
        "UPDATE pil_archive_claims SET node_digest='bad'",
        "DELETE FROM pil_archive_members WHERE ordinal=1",
        "UPDATE pil_archive_content SET content=decode('00','hex')",
    ],
)
def test_corruption_is_never_success(archive_dsn, tmp_path, mutation):
    _, archive = setup(archive_dsn)
    first, content = completed(tmp_path)
    archive.append(first, content)
    table = mutation.split()[1 if mutation.startswith("UPDATE") else 2]
    with psycopg.connect(archive_dsn) as c:
        c.execute(sql.SQL("ALTER TABLE {} DISABLE TRIGGER USER").format(sql.Identifier(table)))
        c.execute(cast(LiteralString, mutation))
    # Changed key is not-found for original lookup, but scoped history must detect corrupt row.
    if "SET execution_digest" not in mutation:
        for read in (archive.load, archive.content):
            with pytest.raises(ArchiveIntegrityError):
                read(first.scope, first.execution_digest)
    with pytest.raises(ArchiveIntegrityError):
        archive.history(first.scope)
