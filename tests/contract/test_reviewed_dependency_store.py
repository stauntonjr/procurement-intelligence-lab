from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ApprovedCorrectionRef,
    ArchivedClaimRef,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewOutcome
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyConflictError,
    DependencyContractError,
    DependencyIntegrityError,
    DependencyUnavailableError,
)
from tests.bom_stage_fixtures import AT
from tests.contract.test_dependency_store import declaration, store
from tests.contract.test_document_review_journal import command, setup
from tests.unit.test_dependencies import claim

pytestmark = pytest.mark.contract


def reviewed(dsn: str, tmp_path: Path, *, approved: bool = True):
    journal, archive, p, content = setup(dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    journal.decide(
        replace(command(task), outcome=ReviewOutcome.APPROVE if approved else ReviewOutcome.REJECT),
        AT + timedelta(seconds=3),
    )
    history = journal.get(p.scope, task.task_id)
    original = declaration(p)
    source = original.roots[0]
    assert type(source) is ArchivedClaimRef and history.decision is not None
    root = ApprovedCorrectionRef(
        source,
        task.task_id,
        task.digest,
        history.decision.decision_id,
        history.correction_id or "not-approved",
    )
    c = claim("reviewed-row", p.previous.assertion_id, root.reference_id)
    c = replace(
        c,
        event=replace(
            c.event,
            provenance=replace(
                c.event.provenance,
                context=replace(
                    c.event.provenance.context,
                    input_snapshot_ids=(p.snapshot_id,),
                    started_at=AT + timedelta(seconds=4),
                ),
            ),
        ),
    )
    graph = replace(
        original,
        request_id="reviewed-request",
        roots=tuple(sorted((*original.roots, root), key=lambda r: r.reference_id)),
        claims=(c,),
    )
    return store(dsn), journal, archive, p, content, graph


def test_capability_is_explicit_and_old_rows_unchanged(archive_dsn: str, tmp_path: Path):
    s, _, archive, p, content, m = reviewed(archive_dsn, tmp_path)
    old = s.append(declaration(p), "recorder", AT + timedelta(seconds=4))
    raw = bootstrap.archive_codec().dumps(old)
    with pytest.raises(DependencyUnavailableError):
        s.append(m, "recorder", AT + timedelta(seconds=4))
    s.initialize_corrections()
    s.initialize_corrections()
    assert bootstrap.archive_codec().dumps(s.get(p.scope, old.snapshot_id)) == raw
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT version FROM pil_dependency_meta").fetchall() == [(1,)]
        assert conn.execute("SELECT version FROM pil_document_review_meta").fetchall() == [(1,)]
        assert conn.execute("SELECT version FROM pil_dependency_correction_meta").fetchall() == [
            (1,)
        ]
    assert archive.content(p.scope, p.snapshot_id) == content


def test_correction_roots_retry_restart_and_atomic_rollback(archive_dsn: str, tmp_path: Path):
    s, _, _, p, _, m = reviewed(archive_dsn, tmp_path)
    s.initialize_corrections()
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(
            pool.map(s.append, [m] * 4, ["recorder"] * 4, [AT + timedelta(seconds=5)] * 4)
        )
    first = receipts[0]
    assert all(x == first for x in receipts)
    assert bootstrap.build_dependency_store(archive_dsn).get(p.scope, first.snapshot_id) == first
    with pytest.raises(DependencyConflictError):
        s.append(m, "other", AT + timedelta(seconds=5))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "ALTER TABLE pil_dependency_correction_roots ADD CONSTRAINT reject_new CHECK (false) NOT VALID"
        )
    with pytest.raises(DependencyUnavailableError):
        s.append(replace(m, request_id="another"), "recorder", AT + timedelta(seconds=5))
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM pil_dependency_roots").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM pil_dependency_correction_roots").fetchone() == (
            1,
        )


def test_missing_reader_and_unsupported_capability_fail_closed(archive_dsn: str, tmp_path: Path):
    from procurement_intelligence_lab.adapters.postgres_dependencies import PostgresDependencyStore

    s, _, archive, _, _, m = reviewed(archive_dsn, tmp_path)
    s.initialize_corrections()
    naked = PostgresDependencyStore(archive_dsn, bootstrap.archive_codec(), archive)
    with pytest.raises(DependencyUnavailableError):
        naked.append(m, "recorder", AT + timedelta(seconds=4))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_dependency_correction_meta DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_dependency_correction_meta SET version=99")
    with pytest.raises(DependencyIntegrityError):
        s.append(m, "recorder", AT + timedelta(seconds=4))


@pytest.mark.parametrize("approved", [True, False])
def test_root_requires_exact_approved_journal_binding(
    archive_dsn: str, tmp_path: Path, approved: bool
):
    s, _, _, _, _, m = reviewed(archive_dsn, tmp_path, approved=approved)
    s.initialize_corrections()
    if approved:
        root = next(r for r in m.roots if type(r) is ApprovedCorrectionRef)
        m = replace(
            m, roots=tuple(replace(r, task_digest="b" * 64) if r is root else r for r in m.roots)
        )
    with pytest.raises(DependencyContractError):
        s.append(m, "recorder", AT + timedelta(seconds=5))
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_retained_root_corruption_is_integrity_failure(archive_dsn: str, tmp_path: Path):
    s, _, _, p, _, m = reviewed(archive_dsn, tmp_path)
    s.initialize_corrections()
    first = s.append(m, "recorder", AT + timedelta(seconds=4))
    with psycopg.connect(archive_dsn) as conn, pytest.raises(psycopg.Error):
        conn.execute("DELETE FROM pil_dependency_correction_roots")
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_dependency_correction_roots DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_dependency_correction_roots SET task_digest='bad'")
    with pytest.raises(DependencyIntegrityError):
        s.get(p.scope, first.snapshot_id)


def test_archive_only_needs_no_review_schema(archive_dsn: str, tmp_path: Path):
    from decimal import Decimal

    from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewProposal
    from tests.contract.test_postgres_archive import inputs
    from tests.contract.test_postgres_archive import store as archive_store

    snapshot, content = inputs(tmp_path)
    archive = archive_store(archive_dsn)
    archive.append(snapshot, content)
    previous = next(a for a in snapshot.assertions if a.predicate.value == "has_quantity")
    p = ReviewProposal(
        snapshot.artifact.source.scope,
        "req",
        snapshot.snapshot_id,
        previous,
        Decimal(8),
        "reason",
        "human",
    )
    s = store(archive_dsn)
    first = s.append(declaration(p), "recorder", AT + timedelta(seconds=4))
    assert s.get(p.scope, first.snapshot_id) == first
    with pytest.raises(DependencyUnavailableError):
        s.initialize_corrections()
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute(
            "SELECT to_regclass('pil_document_review_meta'),to_regclass('pil_dependency_correction_meta')"
        ).fetchone() == (None, None)


def test_corrupt_review_evidence_fails_closed_on_read_and_append(archive_dsn: str, tmp_path: Path):
    s, _, _, p, _, m = reviewed(archive_dsn, tmp_path)
    s.initialize_corrections()
    first = s.append(m, "recorder", AT + timedelta(seconds=4))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_document_review_tasks DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_document_review_tasks SET payload_sha256='bad'")
    with pytest.raises(DependencyIntegrityError):
        s.get(p.scope, first.snapshot_id)
    with pytest.raises(DependencyIntegrityError):
        s.append(replace(m, request_id="another"), "recorder", AT + timedelta(seconds=4))


def test_correction_input_cannot_be_consumed_before_approval(archive_dsn: str, tmp_path: Path):
    s, _, _, _, _, m = reviewed(archive_dsn, tmp_path)
    s.initialize_corrections()
    c = m.claims[0]
    m = replace(
        m,
        claims=(
            replace(
                c,
                event=replace(
                    c.event,
                    provenance=replace(
                        c.event.provenance,
                        context=replace(
                            c.event.provenance.context, started_at=AT + timedelta(seconds=2)
                        ),
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(DependencyContractError):
        s.append(m, "recorder", AT + timedelta(seconds=4))
