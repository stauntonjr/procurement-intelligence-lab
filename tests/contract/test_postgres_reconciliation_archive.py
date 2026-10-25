"""Real Postgres publication and exact existing-producer retention boundaries."""

# pyright: reportPrivateUsage=false
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from typing import Any

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    CompletedReconciliationSnapshot,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
)
from tests.bom_stage_fixtures import AT, SCOPE
from tests.contract.test_postgres_resolved_execution_archive import setup as resolved_setup
from tests.contract.test_reconciliation_operation import service

pytestmark = pytest.mark.contract


def setup(dsn: str, tmp_path: Path):
    _, _, resolved = resolved_setup(dsn)
    s, args, _ = service(tmp_path, empty=False)
    p = s.producer_reader_factory().show(SCOPE, args["producer_digests"][0]).retained
    data = s.producer_reader_factory().content(SCOPE, p.completed.execution_digest)
    retained = resolved.append(p.completed, data)
    s = replace(
        s, producer_reader_factory=lambda: bootstrap.build_resolved_execution_archive_reader(dsn)
    )
    completed = CompletedReconciliationSnapshot(s.execute(**args))
    archive = bootstrap.build_reconciliation_archive(dsn)
    archive.initialize()
    return archive, completed, retained


def test_explicit_predecessor_readiness(archive_dsn: str, tmp_path: Path):
    archive = bootstrap.build_reconciliation_archive(archive_dsn)
    with pytest.raises(ArchiveUnavailableError):
        archive.initialize()
    archive, c, _ = setup(archive_dsn, tmp_path)
    archive.initialize()
    archive.check_ready()
    assert archive.append(c).completed == c


def test_atomic_result_and_exact_producer_links(archive_dsn: str, tmp_path: Path):
    archive, c, p = setup(archive_dsn, tmp_path)
    retained = archive.append(c)
    assert retained.receipt.producer_receipts == (p.receipt,)
    assert archive.load(c.scope, c.execution_digest) == retained
    assert archive.history(c.scope).receipts == (retained.receipt,)
    with pytest.raises(ArchiveNotFoundError):
        archive.load(replace(c.scope, version="foreign"), c.execution_digest)
    with psycopg.connect(archive_dsn) as conn:
        for table in ("pil_reconciliations", "pil_reconciliation_producers"):
            with pytest.raises(psycopg.Error), conn.transaction():
                conn.execute(f"DELETE FROM {table}")


def test_concurrent_retry_first_retention(archive_dsn: str, tmp_path: Path):
    archive, c, _ = setup(archive_dsn, tmp_path)
    barrier = Barrier(2)

    def append(_: int):
        barrier.wait()
        return archive.append(c)

    with ThreadPoolExecutor(2) as pool:
        a, b = list(pool.map(append, range(2)))
    assert a == b and len(archive.history(c.scope).receipts) == 1


def test_raw_format_retry_preserves_first_audit(archive_dsn: str, tmp_path: Path):
    archive, c, _ = setup(archive_dsn, tmp_path)
    first = archive.append(c)
    o = c.execution.output
    authority = replace(o.inputs.authority, raw_json=b" \n" + o.inputs.authority.raw_json)
    later = replace(
        c,
        execution=replace(
            c.execution,
            output=replace(o, inputs=replace(o.inputs, authority=authority)),
            completed_at=AT + timedelta(seconds=9),
        ),
    )
    assert archive.append(later) == first
    assert later.execution.receipt_digest != first.completed.execution.receipt_digest


def test_rollback_at_every_append_boundary(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    archive, c, _ = setup(archive_dsn, tmp_path)

    def fail(*args: Any, **kwargs: Any):
        raise RuntimeError("injected rollback")

    monkeypatch.setattr(archive, "_append_links", fail)
    with pytest.raises(RuntimeError):
        archive.append(c)
    assert archive.history(c.scope).receipts == ()
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_reconciliation_producers").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM pil_resolved_executions").fetchone() == (1,)


def test_lost_ack_requires_scoped_recovery(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    archive, c, _ = setup(archive_dsn, tmp_path)
    source = archive.resolved.prefix.source
    original = source._connection

    @contextmanager
    def lost():
        with original() as conn:
            yield conn
        raise ArchiveUnavailableError("injected acknowledgement loss")

    monkeypatch.setattr(source, "_connection", lost)
    with pytest.raises(ArchiveUnavailableError):
        archive.append(c)
    monkeypatch.setattr(source, "_connection", original)
    assert archive.load(c.scope, c.execution_digest).completed == c


def test_resealed_producer_join_and_policy_fail_integrity(archive_dsn: str, tmp_path: Path):
    archive, c, _ = setup(archive_dsn, tmp_path)
    archive.append(c)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_reconciliation_producers DISABLE TRIGGER USER")
        conn.execute(
            "UPDATE pil_reconciliation_producers SET retained_receipt_digest=%s", ("0" * 64,)
        )
    with pytest.raises(ArchiveIntegrityError):
        archive.load(c.scope, c.execution_digest)


def test_digest_collision_compares_full_semantic_content(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
        ReconciliationOperationReceipt,
    )
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveConflictError

    monkeypatch.setattr(
        ReconciliationOperationReceipt, "execution_digest", property(lambda _: "a" * 64)
    )
    archive, first, _ = setup(archive_dsn, tmp_path / "one")
    archive.append(first)
    _, different, _ = setup(archive_dsn, tmp_path / "two")
    with pytest.raises(ArchiveConflictError):
        archive.append(different)


def test_present_result_with_missing_join_is_integrity(archive_dsn: str, tmp_path: Path):
    archive, c, _ = setup(archive_dsn, tmp_path)
    archive.append(c)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_reconciliation_producers DISABLE TRIGGER USER")
        conn.execute("DELETE FROM pil_reconciliation_producers")
    with pytest.raises(ArchiveIntegrityError):
        archive.load(c.scope, c.execution_digest)
    with pytest.raises(ArchiveIntegrityError):
        archive.history(c.scope)


def test_rehashed_policy_payload_is_integrity(archive_dsn: str, tmp_path: Path):
    from hashlib import sha256

    archive, c, _ = setup(archive_dsn, tmp_path)
    archive.append(c)
    with psycopg.connect(archive_dsn) as conn:
        row = conn.execute("SELECT payload FROM pil_reconciliations").fetchone()
        assert row is not None
        changed = row[0].replace("procurement-governing-claims/v1", "unsupported-policy/v2")
        assert changed != row[0]
        conn.execute("ALTER TABLE pil_reconciliations DISABLE TRIGGER USER")
        conn.execute(
            "UPDATE pil_reconciliations SET payload=%s,payload_sha256=%s",
            (changed, sha256(changed.encode()).hexdigest()),
        )
    with pytest.raises(ArchiveIntegrityError):
        archive.load(c.scope, c.execution_digest)
