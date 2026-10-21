from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewProposal
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyConflictError,
    DependencyNotFoundError,
    DependencyUnavailableError,
    ScopeAuthorizationError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_document_review_journal import command
from tests.contract.test_postgres_archive import inputs, store
from tests.unit.test_source_sku_query import execution

pytestmark = pytest.mark.contract


def setup(dsn: str, tmp_path: Path, rows: str = HEADER + ROW):
    snapshot, content = inputs(tmp_path, rows)
    snapshot = replace(
        snapshot, normalization_policy_parameters=tuple(sorted(POLICY.as_dict().items()))
    )
    archive = store(dsn)
    archive.append(snapshot, content)
    journal = bootstrap.build_document_review_journal(dsn)
    journal.initialize()
    previous = next(a for a in snapshot.assertions if a.predicate.value == "has_quantity")
    proposal = ReviewProposal(
        snapshot.artifact.source.scope,
        "review-request",
        snapshot.snapshot_id,
        previous,
        Decimal(8),
        "source check",
        "human",
    )
    return journal, archive, proposal, content


def context(scope: StateScope, *, review: bool = True):
    return RequestContext(
        "human",
        scope.tenant_id,
        scope.project_id,
        scope.site_id,
        frozenset(
            {Permission.READ_EVIDENCE, Permission.REVIEW} if review else {Permission.READ_EVIDENCE}
        ),
        "source-query",
    )


def service(dsn: str):
    assert hasattr(bootstrap, "build_archived_bom_query_service")
    bootstrap.build_dependency_store(dsn).initialize()
    return bootstrap.build_archived_bom_query_service(dsn, clock=lambda: AT + timedelta(seconds=3))


def test_actual_producer_retry_restart_and_human_correction_impact(
    archive_dsn: str, tmp_path: Path
):
    journal, archive, p, content = setup(archive_dsn, tmp_path)
    (tmp_path / "source.xlsx").unlink()
    s = service(archive_dsn)
    ctx = context(p.scope)
    run = execution(p.snapshot_id)
    first = s.execute(p.scope, p.snapshot_id, "query-request", run, context=ctx)
    again = service(archive_dsn).execute(p.scope, p.snapshot_id, "query-request", run, context=ctx)
    assert first.as_dict() == again.as_dict()
    assert first.query.value == ("GPU-A",)
    sku = first.query.inputs[0]
    task = journal.propose(
        replace(p, previous=sku, proposed_value="GPU-B"), AT + timedelta(seconds=4)
    )
    journal.decide(command(task), AT + timedelta(seconds=5))
    impact = bootstrap.build_correction_impact_service(archive_dsn).inspect(
        p.scope,
        first.registration.snapshot_id,
        task.task_id,
        as_of=AT + timedelta(seconds=5),
        max_depth=1,
        context=ctx,
    )
    assert [x["reference_id"] for x in impact["affected"]] == [first.query.reference_id]
    assert impact["review"]["correction"]["value"] == {"type": "str", "value": "GPU-B"}
    assert first.query.value == again.query.value == ("GPU-A",)
    assert impact["recomputation_executed"] is False
    assert archive.content(p.scope, p.snapshot_id) == content
    quantity = journal.propose(replace(p, request_id="quantity"), AT + timedelta(seconds=4))
    journal.decide(
        replace(command(quantity), request_id="quantity-decision"), AT + timedelta(seconds=5)
    )
    with pytest.raises(DependencyNotFoundError):
        bootstrap.build_correction_impact_service(archive_dsn).inspect(
            p.scope,
            first.registration.snapshot_id,
            quantity.task_id,
            as_of=AT + timedelta(seconds=5),
            max_depth=1,
            context=ctx,
        )


def test_changed_reused_context_actor_or_source_conflicts(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = service(archive_dsn)
    ctx = context(p.scope)
    run = execution(p.snapshot_id)
    first = s.execute(p.scope, p.snapshot_id, "same-request", run, context=ctx)
    for changed, actor in [
        (replace(run, code_revision="another"), ctx),
        (run, replace(ctx, principal_id="other")),
    ]:
        with pytest.raises(DependencyConflictError):
            s.execute(p.scope, p.snapshot_id, "same-request", changed, context=actor)
    later = s.execute(
        p.scope, p.snapshot_id, "new-request", replace(run, code_revision="another"), context=ctx
    )
    assert (
        later.query.value == first.query.value
        and later.query.reference_id != first.query.reference_id
    )
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (2,)


def test_no_success_when_dependency_registration_unavailable(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    assert hasattr(bootstrap, "build_archived_bom_query_service")
    s = bootstrap.build_archived_bom_query_service(
        archive_dsn, clock=lambda: AT + timedelta(seconds=3)
    )
    with pytest.raises(DependencyUnavailableError):
        s.execute(
            p.scope, p.snapshot_id, "request", execution(p.snapshot_id), context=context(p.scope)
        )


class NoIO:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError("unexpected I/O")


def test_authorization_identifiers_and_context_fail_before_io():
    from procurement_intelligence_lab.application.archived_bom_queries import (
        ArchivedBomQueryService,
    )
    from procurement_intelligence_lab.domains.procurement.source_queries import SourceSkuQuery

    s = ArchivedBomQueryService(cast(Any, NoIO()), cast(Any, NoIO()), SourceSkuQuery, lambda: AT)
    scope = StateScope("synthetic", "p", "lab", "1")
    ctx = context(scope)
    run = replace(execution("snapshot"), started_at=AT)
    with pytest.raises(ScopeAuthorizationError):
        s.execute(scope, "snapshot", "request", run, context=context(scope, review=False))
    with pytest.raises(ScopeAuthorizationError):
        s.execute(replace(scope, site_id="foreign"), "snapshot", "request", run, context=ctx)
    for snapshot, request in [("bad\ud800", "request"), ("snapshot", ""), ("snapshot", "x" * 501)]:
        with pytest.raises(SourceQueryContractError):
            s.execute(scope, snapshot, request, run, context=ctx)
    for invalid in [
        replace(run, code_revision="bad\ud800"),
        replace(run, input_snapshot_ids=("foreign",)),
        replace(run, started_at=AT + timedelta(days=1)),
        replace(run, environment=(("raw", "no"),)),
    ]:
        with pytest.raises(SourceQueryContractError):
            s.execute(scope, "snapshot", "request", invalid, context=ctx)


def test_injected_producer_cannot_substitute_execution_or_snapshot(
    archive_dsn: str, tmp_path: Path
):
    from procurement_intelligence_lab.domains.procurement.source_queries import SourceSkuQuery

    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = service(archive_dsn)
    ctx = context(p.scope)
    run = execution(p.snapshot_id)

    def changed_execution(snapshot: Any, provenance: Any):
        return SourceSkuQuery(
            snapshot,
            replace(provenance, context=replace(provenance.context, parent_run_id="unrequested")),
        )

    with pytest.raises(SourceQueryContractError):
        replace(s, producer=changed_execution).execute(
            p.scope, p.snapshot_id, "changed", run, context=ctx
        )
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_actual_parser_with_real_storage_and_typed_context(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    import json
    import sys
    from dataclasses import asdict

    from procurement_intelligence_lab.interfaces.archived_bom_query import main

    _, _, p, _ = setup(archive_dsn, tmp_path)
    bootstrap.build_dependency_store(archive_dsn).initialize()
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    run = tmp_path / "query-context.json"
    data = {
        "run_id": "parser-run",
        "code_revision": "test",
        "started_at": execution(p.snapshot_id).started_at.isoformat(),
    }
    run.write_text(json.dumps(data))
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setenv("PIL_DOCUMENT_REVIEWER_ID", "parser-human")
    args = [
        "archived-bom-query",
        "--scope",
        str(scope),
        "--snapshot-id",
        p.snapshot_id,
        "--request-id",
        "parser-request",
        "--context",
        str(run),
    ]
    monkeypatch.setattr(sys, "argv", args)
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"]["value"] == ["GPU-A"]
    run.write_text(json.dumps({**data, "code_revision": "changed"}))
    assert main() == 2
    assert json.loads(capsys.readouterr().err)["code"] == "pil.policy.dependency_conflict"
    run.write_text("[]")
    assert main() == 2
    assert json.loads(capsys.readouterr().err)["code"] == "pil.input.source_query_invalid"
    monkeypatch.delenv("PIL_DOCUMENT_REVIEWER_ID")
    assert main() == 2
    assert json.loads(capsys.readouterr().err)["category"] == "authorization"


def test_recording_time_follows_actual_producer_completion(archive_dsn: str, tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.source_queries import SourceSkuQuery

    _, _, p, _ = setup(archive_dsn, tmp_path)
    s = service(archive_dsn)
    produced = False

    def produce(snapshot: Any, provenance: Any):
        nonlocal produced
        result = SourceSkuQuery(snapshot, provenance)
        produced = True
        return result

    def clock():
        return AT + timedelta(seconds=4 if produced else 3)

    result = replace(s, producer=produce, clock=clock).execute(
        p.scope, p.snapshot_id, "clock-order", execution(p.snapshot_id), context=context(p.scope)
    )
    assert result.registration.recorded_at == AT + timedelta(seconds=4)


@pytest.mark.parametrize("count", [32, 33])
def test_actual_registration_respects_direct_input_budget(
    archive_dsn: str, tmp_path: Path, count: int
):
    _, _, p, _ = setup(
        archive_dsn,
        tmp_path,
        HEADER + "".join(ROW.replace("7", str(i)) for i in range(2, count + 2)),
    )
    s = service(archive_dsn)
    if count == 33:
        with pytest.raises(SourceQueryContractError):
            s.execute(
                p.scope,
                p.snapshot_id,
                "boundary",
                execution(p.snapshot_id),
                context=context(p.scope),
            )
    else:
        result = s.execute(
            p.scope, p.snapshot_id, "boundary", execution(p.snapshot_id), context=context(p.scope)
        )
        assert len(result.registration.manifest.roots) == 32
        assert len(result.registration.manifest.claims[0].inputs) == 32
        assert result.query.value == ("GPU-A",)
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (
            0 if count == 33 else 1,
        )
