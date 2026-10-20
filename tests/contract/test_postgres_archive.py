from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.application.archived_documents import snapshot_for
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveConflictError,
    ArchiveIntegrityError,
    ArchiveNotFoundError,
    ArchiveUnavailableError,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source

pytestmark = pytest.mark.contract


def inputs(tmp_path: Path, rows: str = HEADER + ROW):
    path = workbook(tmp_path / "source.xlsx", rows)
    result = bootstrap.build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(source(path))
    return snapshot_for(result), path.read_bytes()


def store(dsn: str):
    assert hasattr(bootstrap, "build_assertion_archive")
    result = bootstrap.build_assertion_archive(dsn)
    result.initialize()
    return result


def test_restart_retry_preserves_complete_claims_and_exact_bytes(archive_dsn: str, tmp_path: Path):
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    receipt = archive.append(snapshot, content)
    again = bootstrap.build_assertion_archive(archive_dsn)
    assert again.append(snapshot, content) == receipt
    assert again.load(snapshot.artifact.source.scope, snapshot.snapshot_id) == (receipt, snapshot)
    assert again.content(receipt.scope, receipt.snapshot_id) == content
    assert again.history(receipt.scope) == (receipt,)
    for scope in (
        replace(receipt.scope, tenant_id="foreign"),
        replace(receipt.scope, version="other"),
    ):
        assert again.history(scope) == ()
        with pytest.raises(ArchiveNotFoundError):
            again.load(scope, receipt.snapshot_id)
        with pytest.raises(ArchiveNotFoundError):
            again.content(scope, receipt.snapshot_id)


def test_malformed_stored_record_fails_typed_after_checksum_validation(
    archive_dsn: str, tmp_path: Path
) -> None:
    import json
    from hashlib import sha256

    from procurement_intelligence_lab.adapters.semantic_codec import digest

    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    receipt = archive.append(snapshot, content)
    node: dict[str, object] = {"kind": "DocumentSnapshot", "fields": json.loads("[[]]")}
    key = digest(node)
    payload = json.dumps({"schema": 1, "root": ["ref", key], "records": {key: node}})
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_archive_batches DISABLE TRIGGER USER")
        conn.execute(
            "UPDATE pil_archive_batches SET payload=%s,payload_sha256=%s",
            (payload, sha256(payload.encode()).hexdigest()),
        )
        conn.execute("ALTER TABLE pil_archive_batches ENABLE TRIGGER USER")
    for read in (archive.load, archive.content):
        with pytest.raises(ArchiveIntegrityError):
            read(receipt.scope, receipt.snapshot_id)
    with pytest.raises(ArchiveIntegrityError):
        archive.history(receipt.scope)


def test_concurrent_identical_appends_commit_once(archive_dsn: str, tmp_path: Path):
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(archive.append, [snapshot] * 16, [content] * 16))
    assert all(x == receipts[0] for x in receipts)
    assert archive.history(snapshot.artifact.source.scope) == (receipts[0],)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_archive_claims").fetchone() == (4,)


def test_conflicting_revisions_and_empty_batches_survive(archive_dsn: str, tmp_path: Path):
    archive = store(archive_dsn)
    first, content1 = inputs(tmp_path)
    second, content2 = inputs(tmp_path, HEADER + ROW.replace("<v>0.5</v>", "<v>0</v>"))
    empty, content3 = inputs(tmp_path, HEADER)
    receipts = [
        archive.append(s, c) for s, c in [(first, content1), (second, content2), (empty, content3)]
    ]
    assert len(archive.history(first.artifact.source.scope)) == 3
    assert len({x.sequence for x in receipts}) == 3
    assert archive.load(receipts[2].scope, empty.snapshot_id)[1].assertions == ()
    assert archive.load(receipts[0].scope, first.snapshot_id)[1] == first


def test_same_identity_different_payload_fails_without_overwriting(
    archive_dsn: str, tmp_path: Path
):
    from datetime import timedelta

    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    receipt = archive.append(snapshot, content)
    prov = replace(
        snapshot.structured.provenance,
        context=replace(
            snapshot.structured.provenance.context, started_at=AT + timedelta(seconds=1)
        ),
    )
    structured = replace(snapshot.structured, provenance=prov)
    changed = replace(
        snapshot,
        structured=structured,
        mapped=replace(snapshot.mapped, source_document=structured),
        transformations=(
            snapshot.transformations[0],
            replace(snapshot.transformations[1], provenance=prov),
            *snapshot.transformations[2:],
        ),
    )
    assert changed.snapshot_id == snapshot.snapshot_id
    with pytest.raises(ArchiveConflictError):
        archive.append(changed, content)
    assert archive.load(receipt.scope, receipt.snapshot_id) == (receipt, snapshot)


def test_mid_write_failure_rolls_back_every_table(archive_dsn: str, tmp_path: Path):
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION fail_member() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure'; END $$"
        )
        conn.execute(
            "CREATE TRIGGER fail_member BEFORE INSERT ON pil_archive_members FOR EACH ROW EXECUTE FUNCTION fail_member()"
        )
    with pytest.raises(ArchiveUnavailableError):
        archive.append(snapshot, content)
    with psycopg.connect(archive_dsn) as conn:
        for table in (
            "pil_archive_content",
            "pil_archive_batches",
            "pil_archive_claims",
            "pil_archive_members",
        ):
            assert conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)


def test_sql_mutation_guards_and_corrupt_data_fail_closed(archive_dsn: str, tmp_path: Path):
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    receipt = archive.append(snapshot, content)
    for statement in (
        "DELETE FROM pil_archive_batches",
        "UPDATE pil_archive_claims SET node_digest='bad'",
        "TRUNCATE pil_archive_members",
    ):
        with psycopg.connect(archive_dsn) as conn, pytest.raises(psycopg.Error):
            conn.execute(statement)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_archive_content DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_archive_content SET content=decode('00','hex')")
        conn.execute("ALTER TABLE pil_archive_content ENABLE TRIGGER USER")
    with pytest.raises(ArchiveIntegrityError):
        archive.content(receipt.scope, receipt.snapshot_id)
    with pytest.raises(ArchiveIntegrityError):
        archive.load(receipt.scope, receipt.snapshot_id)


@pytest.mark.parametrize("change", ["payload", "members", "claims", "schema"])
def test_corrupt_metadata_and_membership_cannot_report_success(
    archive_dsn: str, tmp_path: Path, change: str
) -> None:
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    receipt = archive.append(snapshot, content)
    table = {
        "payload": "pil_archive_batches",
        "members": "pil_archive_members",
        "claims": "pil_archive_claims",
        "schema": "pil_archive_meta",
    }[change]
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(sql.SQL("ALTER TABLE {} DISABLE TRIGGER USER").format(sql.Identifier(table)))
        if change == "payload":
            conn.execute("UPDATE pil_archive_batches SET payload='{}'")
        elif change == "members":
            conn.execute("DELETE FROM pil_archive_members WHERE ordinal=1")
        elif change == "claims":
            conn.execute("UPDATE pil_archive_claims SET node_digest='bad'")
        else:
            conn.execute("UPDATE pil_archive_meta SET version=2")
        conn.execute(sql.SQL("ALTER TABLE {} ENABLE TRIGGER USER").format(sql.Identifier(table)))
    with pytest.raises(ArchiveIntegrityError):
        archive.load(receipt.scope, receipt.snapshot_id)
    with pytest.raises(ArchiveIntegrityError):
        archive.history(receipt.scope)
    if change == "schema":
        with pytest.raises(ArchiveIntegrityError):
            archive.initialize()


def test_bad_content_and_uninitialized_backend_do_not_materialize(
    archive_dsn: str, tmp_path: Path
) -> None:
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    snapshot, content = inputs(tmp_path)
    archive = bootstrap.build_assertion_archive(archive_dsn)
    with pytest.raises(ArchiveUnavailableError):
        archive.append(snapshot, content)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT to_regclass('pil_archive_meta')").fetchone() == (None,)
    archive.initialize()
    archive.initialize()
    for wrong in (b"", content + b"changed"):
        with pytest.raises(ArchiveContractError):
            archive.append(snapshot, wrong)
    assert archive.history(snapshot.artifact.source.scope) == ()
