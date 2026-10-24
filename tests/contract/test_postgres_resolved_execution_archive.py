"""Actual atomic source/prefix/catalog/sixth retention; no synthetic storage substitute."""
# pyright: reportPrivateUsage=false

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from typing import Any, LiteralString, cast

import psycopg
import pytest
from psycopg import sql

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import load_candidate_input
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
)
from tests.bom_stage_fixtures import AT
from tests.planned_execution_archive_fixtures import parameters
from tests.resolved_execution_fixtures import catalog_wire, completed_resolved

pytestmark = pytest.mark.contract


def setup(dsn: str):
    source = bootstrap.build_assertion_archive(dsn)
    source.initialize()
    prefix = bootstrap.build_planned_execution_archive(dsn)
    prefix.initialize()
    archive = bootstrap.build_resolved_execution_archive(dsn)
    archive.initialize()
    return source, prefix, archive


def test_explicit_capability_and_atomic_source_prefix_catalog_resolution(
    archive_dsn: str, tmp_path: Path
):
    archive = bootstrap.build_resolved_execution_archive(archive_dsn)
    with pytest.raises(ArchiveUnavailableError):
        archive.initialize()
    source, prefix, archive = setup(archive_dsn)
    archive.initialize()
    completed, content = completed_resolved(tmp_path)
    retained = archive.append(completed, content)
    fresh = bootstrap.build_resolved_execution_archive(archive_dsn)
    assert canonical(fresh.load(completed.scope, completed.execution_digest)) == canonical(retained)
    assert fresh.content(completed.scope, completed.execution_digest) == content
    assert (
        source.load(completed.scope, completed.prefix.snapshot.snapshot_id)[1]
        == completed.prefix.snapshot
    )
    assert (
        prefix.load(completed.scope, completed.prefix.execution_digest) == retained.retained_prefix
    )
    foreign = replace(completed.scope, version="foreign")
    with pytest.raises(ArchiveNotFoundError):
        fresh.load(foreign, completed.execution_digest)
    assert not fresh.history(foreign).receipts


def test_existing_prefix_receipt_remains_distinct_from_current_prefix(
    archive_dsn: str, tmp_path: Path
):
    _, prefix, archive = setup(archive_dsn)
    completed, content = completed_resolved(tmp_path)
    early = replace(
        completed.prefix,
        execution=replace(
            completed.execution.prefix, completed_at=AT + timedelta(microseconds=500000)
        ),
    )
    first = prefix.append(early, content)
    retained = archive.append(completed, content)
    assert retained.retained_prefix == first
    assert (
        retained.completed.execution.prefix.receipt_digest
        != first.completed.execution.receipt_digest
    )
    later = replace(
        completed.execution,
        prefix=replace(completed.execution.prefix, completed_at=AT + timedelta(seconds=2)),
        candidate_input=load_candidate_input(json.dumps(catalog_wire(), indent=2).encode()),
        completed_at=AT + timedelta(seconds=3),
    )
    repeated = archive.append(
        CompletedResolvedPrefixSnapshot.from_execution(later, parameters()), content
    )
    assert canonical(repeated) == canonical(retained)
    assert (
        repeated.completed.execution.candidate_input.raw_sha256 != later.candidate_input.raw_sha256
    )


def test_same_computation_concurrent_first_retention(archive_dsn: str, tmp_path: Path):
    _, _, archive = setup(archive_dsn)
    completed, content = completed_resolved(tmp_path)
    barrier = Barrier(4)

    def append(_: int):
        barrier.wait(timeout=10)
        return archive.append(completed, content)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(append, range(4)))
    assert all(canonical(r) == canonical(results[0]) for r in results)
    assert len(archive.history(completed.scope).receipts) == 1


@pytest.mark.parametrize(
    "table", ["pil_archive_batches", "pil_planned_executions", "pil_resolved_executions"]
)
def test_rollback_at_each_publication_boundary(archive_dsn: str, tmp_path: Path, table: str):
    _, _, archive = setup(archive_dsn)
    completed, content = completed_resolved(tmp_path)
    with psycopg.connect(archive_dsn) as c:
        c.execute(
            "CREATE FUNCTION fail_resolved_write() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test'; END $$"
        )
        c.execute(
            sql.SQL(
                "CREATE TRIGGER fail_resolved_write BEFORE INSERT ON {} FOR EACH ROW EXECUTE FUNCTION fail_resolved_write()"
            ).format(sql.Identifier(table))
        )
    with pytest.raises(ArchiveUnavailableError):
        archive.append(completed, content)
    with psycopg.connect(archive_dsn) as c:
        for checked_table in (
            "pil_archive_content",
            "pil_archive_batches",
            "pil_archive_claims",
            "pil_archive_members",
            "pil_planned_executions",
            "pil_resolved_executions",
        ):
            assert c.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(checked_table))
            ).fetchone() == (0,)


def test_ack_loss_requires_scoped_recovery(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, archive = setup(archive_dsn)
    completed, content = completed_resolved(tmp_path)
    original = archive.prefix.source._connection

    @contextmanager
    def lose_ack():
        with original() as c:
            yield c
        raise ArchiveUnavailableError("acknowledgement unavailable")

    monkeypatch.setattr(archive.prefix.source, "_connection", lose_ack)
    with pytest.raises(ArchiveUnavailableError):
        archive.append(completed, content)
    fresh = bootstrap.build_resolved_execution_archive(archive_dsn)
    assert fresh.load(completed.scope, completed.execution_digest).completed == completed
    assert len(fresh.history(completed.scope).receipts) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE pil_resolved_executions SET retained_prefix_receipt_digest=repeat('a',64)",
        "UPDATE pil_resolved_executions SET payload_sha256='bad'",
        "UPDATE pil_planned_executions SET retained_receipt_digest=repeat('b',64)",
        "DELETE FROM pil_archive_members WHERE ordinal=1",
        "UPDATE pil_archive_content SET content=decode('00','hex')",
    ],
)
def test_rehashed_catalog_policy_and_source_corruption_rejects(
    archive_dsn: str, tmp_path: Path, mutation: str
):
    _, _, archive = setup(archive_dsn)
    completed, content = completed_resolved(tmp_path)
    archive.append(completed, content)
    table = mutation.split()[1 if mutation.startswith("UPDATE") else 2]
    with psycopg.connect(archive_dsn) as c:
        c.execute(sql.SQL("ALTER TABLE {} DISABLE TRIGGER USER").format(sql.Identifier(table)))
        c.execute(cast(LiteralString, mutation))
    with pytest.raises(ArchiveIntegrityError):
        archive.load(completed.scope, completed.execution_digest)
    with pytest.raises(ArchiveIntegrityError):
        archive.history(completed.scope)


def test_digest_collision_preserves_full_computation_equality(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, archive = setup(archive_dsn)
    first, content = completed_resolved(tmp_path)
    archive.append(first, content)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other, content2 = completed_resolved(other_dir)
    key = first.execution_digest
    monkeypatch.setattr(type(first.execution), "execution_digest", property(lambda _: key))
    with pytest.raises(ArchiveConflictError):
        archive.append(other, content2)


@pytest.mark.parametrize("table", ["pil_resolved_execution_meta", "pil_resolved_executions"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
def test_resolved_sql_records_are_immutable(archive_dsn: str, table: str, operation: str):
    setup(archive_dsn)
    statement = (
        f"UPDATE {table} SET " + ("version=version" if table.endswith("meta") else "scope=scope")
        if operation == "UPDATE"
        else f"{operation} " + ("FROM " if operation == "DELETE" else "") + table
    )
    with psycopg.connect(archive_dsn) as c, pytest.raises(psycopg.Error):
        c.execute(cast(LiteralString, statement))


@pytest.mark.parametrize(
    "limit,after", [(0, 0), (201, 0), (True, 0), (1.5, 0), (1, -1), (1, True), (1, 0.5)]
)
def test_resolved_history_bounds_fail_before_storage(
    archive_dsn: str, tmp_path: Path, limit: Any, after: Any
):
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    _, _, archive = setup(archive_dsn)
    completed, _ = completed_resolved(tmp_path)
    with pytest.raises(ArchiveContractError):
        archive.history(completed.scope, limit=limit, after_sequence=after)


def test_resolved_history_exclusive_cursor_and_positive_more_evidence(
    archive_dsn: str, tmp_path: Path
):
    _, _, archive = setup(archive_dsn)
    first, content = completed_resolved(tmp_path)
    a = archive.append(first, content).receipt
    other_dir = tmp_path / "second"
    other_dir.mkdir()
    second, content2 = completed_resolved(other_dir)
    b = archive.append(second, content2).receipt
    page = archive.history(first.scope, limit=1)
    assert page.receipts == (a,) and page.has_more and page.next_after_sequence == a.sequence
    page = archive.history(first.scope, limit=1, after_sequence=a.sequence)
    assert page.receipts == (b,) and not page.has_more and page.next_after_sequence is None
    assert not archive.history(first.scope, after_sequence=b.sequence).receipts


def test_resolved_init_requires_both_predecessors(archive_dsn: str):
    archive = bootstrap.build_resolved_execution_archive(archive_dsn)
    bootstrap.build_assertion_archive(archive_dsn).initialize()
    with pytest.raises(ArchiveUnavailableError):
        archive.initialize()
    with psycopg.connect(archive_dsn) as c:
        assert c.execute("SELECT to_regclass('pil_resolved_execution_meta')").fetchone() == (None,)
    bootstrap.build_planned_execution_archive(archive_dsn).initialize()
    with pytest.raises(ArchiveUnavailableError):
        archive.check_ready()
    archive.initialize()
    archive.check_ready()
