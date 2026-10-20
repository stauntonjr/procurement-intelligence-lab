from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    DocumentReviewTask,
    ReviewDecisionCommand,
    ReviewOutcome,
    ReviewProposal,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ReviewConflictError,
    ReviewIntegrityError,
    ReviewNotFoundError,
    ReviewUnavailableError,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from tests.bom_stage_fixtures import AT
from tests.contract.test_postgres_archive import inputs, store

pytestmark = pytest.mark.contract


def setup(archive_dsn: str, tmp_path: Path):
    assert hasattr(bootstrap, "build_document_review_journal")
    snapshot, content = inputs(tmp_path)
    archive = store(archive_dsn)
    archive.append(snapshot, content)
    journal = bootstrap.build_document_review_journal(archive_dsn)
    journal.initialize()
    previous = next(a for a in snapshot.assertions if a.predicate.value == "has_quantity")
    proposal = ReviewProposal(
        snapshot.artifact.source.scope,
        "req-1",
        snapshot.snapshot_id,
        previous,
        Decimal(8),
        "interpretation correction",
        "human",
    )
    return journal, archive, proposal, content


def command(task: DocumentReviewTask):
    return ReviewDecisionCommand(
        task.proposal.scope,
        "decision-1",
        task.task_id,
        task.digest,
        ReviewOutcome.APPROVE,
        "reviewer",
        "source evidence checked",
    )


def test_restart_retry_and_as_of_keep_source_and_correction_separate(
    archive_dsn: str, tmp_path: Path
):
    journal, archive, p, content = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    assert journal.propose(p, AT + timedelta(days=1)) == task
    decision = journal.decide(command(task), AT + timedelta(seconds=3))
    assert journal.decide(command(task), AT + timedelta(days=1)) == decision
    reopened = bootstrap.build_document_review_journal(archive_dsn)
    assert reopened.get(p.scope, task.task_id).correction_id
    assert reopened.get(p.scope, task.task_id, AT + timedelta(seconds=2)).decision is None
    assert reopened.get(p.scope, task.task_id, decision.recorded_at).decision == decision
    with pytest.raises(ReviewNotFoundError):
        reopened.get(p.scope, task.task_id, AT)
    assert reopened.history(p.scope, AT) == ()
    assert archive.content(p.scope, p.snapshot_id) == content
    retained = archive.load(p.scope, p.snapshot_id)[1]
    assert p.previous in retained.assertions and p.previous.value == Decimal("0.5")
    foreign = replace(p.scope, version="foreign")
    assert reopened.history(foreign) == ()
    with pytest.raises(ReviewNotFoundError):
        reopened.get(foreign, task.task_id)


def test_concurrent_retry_and_terminal_conflicts(archive_dsn: str, tmp_path: Path):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = list(pool.map(journal.propose, [p] * 8, [AT + timedelta(seconds=2)] * 8))
    assert all(t == tasks[0] for t in tasks)
    task = tasks[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        decisions = list(
            pool.map(journal.decide, [command(task)] * 8, [AT + timedelta(seconds=3)] * 8)
        )
    assert all(d == decisions[0] for d in decisions)
    with pytest.raises(ReviewConflictError):
        journal.propose(replace(p, proposed_value=Decimal(9)), task.recorded_at)
    with pytest.raises(ReviewConflictError):
        journal.decide(
            replace(command(task), outcome=ReviewOutcome.REJECT), AT + timedelta(seconds=4)
        )
    with pytest.raises(ReviewConflictError):
        journal.decide(replace(command(task), request_id="new-decision"), AT + timedelta(seconds=4))
    assert len(journal.history(p.scope)) == 1


def test_corrupt_journal_and_sql_guards_fail_closed(archive_dsn: str, tmp_path: Path):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    for operation in (
        "DELETE FROM pil_document_review_tasks",
        "TRUNCATE pil_document_review_tasks",
    ):
        with psycopg.connect(archive_dsn) as conn, pytest.raises(psycopg.Error):
            conn.execute(operation)
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_document_review_tasks DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_document_review_tasks SET payload_sha256='corrupt'")
        conn.execute("ALTER TABLE pil_document_review_tasks ENABLE TRIGGER USER")
    with pytest.raises(ReviewIntegrityError):
        journal.get(p.scope, task.task_id)


def test_missing_init_and_mid_write_error_cannot_report_correction(
    archive_dsn: str, tmp_path: Path
):
    assert hasattr(bootstrap, "build_document_review_journal")
    journal = bootstrap.build_document_review_journal(archive_dsn)
    snapshot, _ = inputs(tmp_path)
    with pytest.raises(ReviewUnavailableError):
        journal.history(snapshot.artifact.source.scope)
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION fail_decision() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fail'; END $$"
        )
        conn.execute(
            "CREATE TRIGGER fail_decision BEFORE INSERT ON pil_document_review_decisions FOR EACH ROW EXECUTE FUNCTION fail_decision()"
        )
    with pytest.raises(ReviewUnavailableError):
        journal.decide(command(task), AT + timedelta(seconds=3))
    assert journal.get(p.scope, task.task_id).decision is None


def test_application_denies_agent_and_cross_scope_before_writes(archive_dsn: str, tmp_path: Path):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    assert hasattr(bootstrap, "build_document_review_service")
    service = bootstrap.build_document_review_service(
        archive_dsn, clock=lambda: AT + timedelta(seconds=2)
    )
    ctx = RequestContext(
        "agent",
        p.scope.tenant_id,
        p.scope.project_id,
        p.scope.site_id,
        frozenset({Permission.READ_EVIDENCE}),
        "test",
    )

    def submit(context: RequestContext, request_id: str = "app-1", value: object = Decimal(8)):
        from typing import cast

        from procurement_intelligence_lab.platform.semantics.values import SemanticValue

        return service.propose(
            scope=p.scope,
            request_id=request_id,
            snapshot_id=p.snapshot_id,
            assertion_id=p.previous.assertion_id,
            proposed_value=cast(SemanticValue, value),
            reason="correct",
            context=context,
        )

    with pytest.raises(ScopeAuthorizationError):
        submit(ctx)
    with pytest.raises(ScopeAuthorizationError):
        submit(replace(ctx, tenant_id="foreign", permissions=frozenset({Permission.REVIEW})))
    assert journal.history(p.scope) == ()
    human = replace(
        ctx,
        principal_id="human",
        permissions=frozenset({Permission.REVIEW, Permission.READ_EVIDENCE}),
    )
    task = submit(human)
    assert task.proposal.proposer_id == "human"
    with pytest.raises(ScopeAuthorizationError):
        service.decide(
            scope=p.scope,
            request_id="d",
            task_id=task.task_id,
            task_digest=task.digest,
            outcome=ReviewOutcome.APPROVE,
            reason="ok",
            context=ctx,
        )
    with pytest.raises(ValueError):
        submit(human, "bad", "8")


def test_review_permission_does_not_implicitly_grant_source_read(archive_dsn: str, tmp_path: Path):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    service = bootstrap.build_document_review_service(
        archive_dsn, clock=lambda: AT + timedelta(seconds=2)
    )
    context = RequestContext(
        "review-only",
        p.scope.tenant_id,
        p.scope.project_id,
        p.scope.site_id,
        frozenset({Permission.REVIEW}),
        "denial",
    )
    with pytest.raises(ScopeAuthorizationError):
        service.propose(
            scope=p.scope,
            request_id="denied",
            snapshot_id=p.snapshot_id,
            assertion_id=p.previous.assertion_id,
            proposed_value=Decimal(8),
            reason="correct",
            context=context,
        )
    assert journal.history(p.scope) == ()


def test_many_conflicting_proposals_and_null_zero_are_retained(archive_dsn: str, tmp_path: Path):
    journal, archive, p, content = setup(archive_dsn, tmp_path)
    values = [None, Decimal(0), Decimal("-0.125"), Decimal("9" * 128 + ".50")]
    for i, value in enumerate(values):
        task = journal.propose(
            replace(p, request_id=f"many-{i}", proposed_value=value), AT + timedelta(seconds=2)
        )
        cmd = replace(
            command(task),
            request_id=f"decision-{i}",
            outcome=ReviewOutcome.REJECT if i == 3 else ReviewOutcome.APPROVE,
        )
        journal.decide(cmd, AT + timedelta(seconds=3))
    results = journal.history(p.scope)
    assert len(results) == 4 and len({r.task.task_id for r in results}) == 4
    assert {str(r.task.proposal.proposed_value) for r in results} == {str(v) for v in values}
    assert sum(r.correction_id is not None for r in results) == 3
    assert archive.content(p.scope, p.snapshot_id) == content


def test_simultaneous_opposed_decisions_leave_one_terminal_receipt(
    archive_dsn: str, tmp_path: Path
):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    commands = [
        command(task),
        replace(command(task), request_id="opposed", outcome=ReviewOutcome.REJECT),
    ]

    def attempt(cmd: ReviewDecisionCommand):
        try:
            return journal.decide(cmd, AT + timedelta(seconds=3))
        except ReviewConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(attempt, commands))
    assert sum(r is not None for r in receipts) == 1
    assert journal.get(p.scope, task.task_id).decision in receipts


@pytest.mark.parametrize("change", ["task_graph", "decision_graph", "schema", "source"])
def test_corrupt_graph_and_source_membership_fail_typed(
    archive_dsn: str, tmp_path: Path, change: str
):
    from hashlib import sha256

    from psycopg import sql

    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    journal.decide(command(task), AT + timedelta(seconds=3))
    table = {
        "task_graph": "pil_document_review_tasks",
        "decision_graph": "pil_document_review_decisions",
        "schema": "pil_document_review_meta",
        "source": "pil_archive_claims",
    }[change]
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(sql.SQL("ALTER TABLE {} DISABLE TRIGGER USER").format(sql.Identifier(table)))
        if change in ("task_graph", "decision_graph"):
            conn.execute(
                sql.SQL("UPDATE {} SET payload=%s,payload_sha256=%s").format(sql.Identifier(table)),
                ("{}", sha256(b"{}").hexdigest()),
            )
        elif change == "schema":
            conn.execute("UPDATE pil_document_review_meta SET version=99")
        else:
            conn.execute("UPDATE pil_archive_claims SET node_digest='corrupt'")
        conn.execute(sql.SQL("ALTER TABLE {} ENABLE TRIGGER USER").format(sql.Identifier(table)))
    with pytest.raises(ReviewIntegrityError):
        journal.get(p.scope, task.task_id)


def test_backdated_and_altered_decisions_leave_pending_task(archive_dsn: str, tmp_path: Path):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    task = journal.propose(p, AT + timedelta(seconds=2))
    with pytest.raises(ValueError):
        journal.decide(command(task), AT)
    with pytest.raises(ReviewConflictError):
        journal.decide(replace(command(task), task_digest="0" * 64), AT + timedelta(seconds=3))
    assert journal.get(p.scope, task.task_id).decision is None


def test_equal_python_source_with_different_retained_encoding_is_not_exact(
    archive_dsn: str, tmp_path: Path
):
    from datetime import timezone

    from procurement_intelligence_lab.platform.semantics.errors import ReviewContractError

    journal, _, p, _ = setup(archive_dsn, tmp_path)
    context = p.previous.context
    assert context is not None
    changed_provenance = replace(
        context.provenance,
        context=replace(
            context.provenance.context,
            started_at=context.provenance.context.started_at.astimezone(
                timezone(timedelta(hours=1))
            ),
        ),
    )
    changed = replace(p.previous, context=replace(context, provenance=changed_provenance))
    assert changed == p.previous and changed.assertion_id == p.previous.assertion_id
    assert bootstrap.archive_codec().dumps(changed) != bootstrap.archive_codec().dumps(p.previous)
    with pytest.raises(ReviewContractError):
        journal.propose(replace(p, previous=changed), AT + timedelta(seconds=2))
    assert journal.history(p.scope) == ()
