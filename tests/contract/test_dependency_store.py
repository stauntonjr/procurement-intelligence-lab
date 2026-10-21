from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import LiteralString, cast

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ArchivedClaimRef,
    ClaimDependency,
    DependencyManifest,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewProposal
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyConflictError,
    DependencyContractError,
    DependencyIntegrityError,
    DependencyNotFoundError,
    DependencyUnavailableError,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from tests.bom_stage_fixtures import AT
from tests.contract.test_document_review_journal import command, setup
from tests.unit.test_dependencies import claim

pytestmark = pytest.mark.contract


def declaration(p: ReviewProposal):
    claims: list[ClaimDependency] = []
    for ref, inputs in [("state", (p.previous.assertion_id,)), ("fact", ("state",))]:
        c = claim(ref, *inputs)
        claims.append(
            replace(
                c,
                event=replace(
                    c.event,
                    provenance=replace(
                        c.event.provenance,
                        context=replace(
                            c.event.provenance.context,
                            input_snapshot_ids=(p.snapshot_id,),
                            started_at=AT,
                        ),
                    ),
                ),
            )
        )
    return DependencyManifest(
        p.scope,
        "dependency-request",
        (ArchivedClaimRef(p.snapshot_id, p.previous.assertion_id),),
        tuple(sorted(claims, key=lambda c: c.reference_id)),
    )


def store(dsn: str):
    assert hasattr(bootstrap, "build_dependency_store")
    s = bootstrap.build_dependency_store(dsn)
    s.initialize()
    return s


def test_dependency_restart_retry_conflict_and_source_preservation(
    archive_dsn: str, tmp_path: Path
):
    _, archive, p, content = setup(archive_dsn, tmp_path)
    s = store(archive_dsn)
    m = declaration(p)
    first = s.append(m, "recorder", AT + timedelta(seconds=4))
    assert s.append(m, "recorder", AT + timedelta(days=1)) == first
    assert bootstrap.build_dependency_store(archive_dsn).get(p.scope, first.snapshot_id) == first
    with pytest.raises(DependencyConflictError):
        s.append(replace(m, claims=()), "recorder", first.recorded_at)
    with pytest.raises(DependencyConflictError):
        s.append(m, "another", first.recorded_at)
    with pytest.raises(DependencyNotFoundError):
        s.get(replace(p.scope, version="other"), first.snapshot_id)
    assert archive.content(p.scope, p.snapshot_id) == content


def test_concurrent_exact_registration_converges(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = store(archive_dsn)
    m = declaration(p)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(s.append, [m] * 8, ["recorder"] * 8, [AT + timedelta(seconds=4)] * 8)
        )
    assert all(x == results[0] for x in results)
    with psycopg.connect(archive_dsn) as c:
        assert c.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (1,)
        assert c.execute("SELECT count(*) FROM pil_dependency_roots").fetchone() == (1,)


def test_missing_source_and_mid_write_failure_roll_back(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = store(archive_dsn)
    m = declaration(p)
    with pytest.raises(DependencyNotFoundError):
        s.append(
            replace(m, roots=(ArchivedClaimRef("absent", p.previous.assertion_id),), claims=()),
            "recorder",
            AT,
        )
    with psycopg.connect(archive_dsn) as c:
        c.execute("ALTER TABLE pil_dependency_roots ADD CONSTRAINT test_reject CHECK (false)")
    with pytest.raises(DependencyUnavailableError):
        s.append(m, "recorder", AT)
    with psycopg.connect(archive_dsn) as c:
        assert c.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_guards_payload_and_membership_corruption_fail_typed(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = store(archive_dsn)
    saved = s.append(declaration(p), "recorder", AT)
    for table in ["pil_dependency_meta", "pil_dependency_snapshots", "pil_dependency_roots"]:
        with psycopg.connect(archive_dsn) as c, pytest.raises(psycopg.Error):
            c.execute(cast(LiteralString, f"DELETE FROM {table}"))
    with psycopg.connect(archive_dsn) as c:
        c.execute("ALTER TABLE pil_dependency_roots DISABLE TRIGGER USER")
        c.execute("DELETE FROM pil_dependency_roots")
    with pytest.raises(DependencyIntegrityError):
        s.get(p.scope, saved.snapshot_id)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE pil_dependency_snapshots SET payload_sha256='bad'",
        "UPDATE pil_dependency_snapshots SET content_digest='bad'",
        "UPDATE pil_dependency_snapshots SET payload='{}'",
        "UPDATE pil_dependency_meta SET version=99",
        "UPDATE pil_archive_batches SET payload_sha256='bad'",
    ],
)
def test_stored_corruption_is_never_empty_success(archive_dsn: str, tmp_path: Path, mutation: str):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = store(archive_dsn)
    saved = s.append(declaration(p), "recorder", AT)
    table = mutation.split()[1]
    with psycopg.connect(archive_dsn) as c:
        c.execute(cast(LiteralString, f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        c.execute(cast(LiteralString, mutation))
    with pytest.raises(DependencyIntegrityError):
        s.get(p.scope, saved.snapshot_id)


def test_missing_init_and_backdating_fail_typed(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    assert hasattr(bootstrap, "build_dependency_store")
    s = bootstrap.build_dependency_store(archive_dsn)
    with pytest.raises(DependencyUnavailableError):
        s.get(p.scope, "missing")
    s.initialize()
    with pytest.raises(DependencyContractError):
        s.append(declaration(p), "recorder", AT - timedelta(seconds=1))


def context(scope: StateScope, permissions: Iterable[Permission]):
    return RequestContext(
        "human", scope.tenant_id, scope.project_id, scope.site_id, frozenset(permissions), "trace"
    )


def test_application_exact_approved_root_as_of_and_denial(archive_dsn: str, tmp_path: Path):
    journal, archive, p, content = setup(archive_dsn, tmp_path)
    store(archive_dsn)
    task = journal.propose(p, AT + timedelta(seconds=1))
    assert hasattr(bootstrap, "build_correction_impact_service")
    service = bootstrap.build_correction_impact_service(
        archive_dsn, clock=lambda: AT + timedelta(seconds=2)
    )
    rw = context(p.scope, [Permission.REVIEW, Permission.READ_EVIDENCE])
    ro = context(p.scope, [Permission.READ_EVIDENCE])
    m = declaration(p)
    with pytest.raises(ScopeAuthorizationError):
        service.register(m, context=context(p.scope, [Permission.REVIEW]))
    saved = service.register(m, context=rw)
    with pytest.raises(DependencyConflictError):
        service.inspect(
            p.scope,
            saved.snapshot_id,
            task.task_id,
            as_of=AT + timedelta(seconds=2),
            max_depth=1,
            context=ro,
        )
    decision = journal.decide(command(task), AT + timedelta(seconds=3))
    result = service.inspect(
        p.scope,
        saved.snapshot_id,
        task.task_id,
        as_of=decision.recorded_at,
        max_depth=1,
        context=ro,
    )
    assert [x["reference_id"] for x in result["affected"]] == ["state"]
    assert result["frontier"] == ["fact"] and not result["traversal_complete"]
    assert result["global_completeness"] == "not_evaluated"
    assert result["recomputation_executed"] is False
    assert (
        result["review"]["correction"]["correction_id"]
        == journal.get(p.scope, task.task_id).correction_id
    )
    with pytest.raises(DependencyNotFoundError):
        service.inspect(p.scope, saved.snapshot_id, task.task_id, as_of=AT, max_depth=1, context=ro)
    with pytest.raises(ScopeAuthorizationError):
        service.inspect(
            replace(p.scope, site_id="foreign"),
            saved.snapshot_id,
            task.task_id,
            as_of=decision.recorded_at,
            max_depth=1,
            context=ro,
        )
    assert archive.content(p.scope, p.snapshot_id) == content


def test_public_parser_real_store_and_explicit_empty_coverage(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    import json
    import sys
    from dataclasses import asdict

    from procurement_intelligence_lab.interfaces.correction_impact import main
    from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewOutcome

    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT)
    journal.decide(command(task), AT)
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    raw = tmp_path / "manifest.json"
    raw.write_text(bootstrap.archive_codec().dumps(replace(declaration(p), claims=())))
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setenv("PIL_DOCUMENT_REVIEWER_ID", "parser-human")

    def invoke(*args: str):
        monkeypatch.setattr(sys, "argv", ["correction-impact", *args])
        code = main()
        out = capsys.readouterr()
        return code, json.loads(out.out if code == 0 else out.err)

    assert invoke("init")[0] == 0
    code, saved = invoke("register", "--scope", str(scope), "--input", str(raw))
    assert code == 0
    args = (
        "inspect",
        "--scope",
        str(scope),
        "--snapshot-id",
        saved["dependency_snapshot_id"],
        "--task-id",
        task.task_id,
        "--as-of",
        "2099-01-01T00:00:00+00:00",
    )
    code, result = invoke(*args)
    assert code == 0
    assert result["affected"] == [] and result["coverage"] == "registered_graph_only"
    assert result["global_completeness"] == "not_evaluated"
    for extra in [("--max-depth", "0"), ("--as-of", "bad"), ("--as-of", "2026-01-01")]:
        code, error = invoke(*args, *extra)
        assert code == 2
        assert error["code"] == "pil.input.dependency_contract_invalid"
    other = journal.propose(
        replace(
            p,
            request_id="another",
            previous=next(
                a
                for a in bootstrap.build_assertion_archive(archive_dsn)
                .load(p.scope, p.snapshot_id)[1]
                .assertions
                if a.predicate.value == "has_unit_price"
            ),
        ),
        AT,
    )
    journal.decide(replace(command(other), request_id="another-decision"), AT)
    assert invoke(*args, "--task-id", other.task_id)[1]["code"] == "pil.input.dependency_not_found"
    rejected = journal.propose(replace(p, request_id="rejected"), AT)
    journal.decide(
        replace(command(rejected), request_id="reject-decision", outcome=ReviewOutcome.REJECT), AT
    )
    assert (
        invoke(*args, "--task-id", rejected.task_id)[1]["code"] == "pil.policy.dependency_conflict"
    )
    monkeypatch.delenv("PIL_DOCUMENT_REVIEWER_ID")
    assert invoke(*args)[1]["category"] == "authorization"


def test_impact_reuses_domain_review_admission_instead_of_only_journal_storage(
    archive_dsn: str, tmp_path: Path
):
    from procurement_intelligence_lab.platform.semantics.errors import ReviewContractError

    journal, _, p, _ = setup(archive_dsn, tmp_path)
    store(archive_dsn)
    task = journal.propose(replace(p, proposed_value="not-a-quantity"), AT)
    journal.decide(command(task), AT)
    service = bootstrap.build_correction_impact_service(archive_dsn, clock=lambda: AT)
    ctx = context(p.scope, [Permission.REVIEW, Permission.READ_EVIDENCE])
    saved = service.register(declaration(p), context=ctx)
    with pytest.raises(ReviewContractError):
        service.inspect(
            p.scope, saved.snapshot_id, task.task_id, as_of=AT, max_depth=2, context=ctx
        )
