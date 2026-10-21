from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewHistory
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyConflictError,
    ScopeAuthorizationError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from tests.bom_stage_fixtures import AT
from tests.contract.test_archived_bom_query import NoIO, context, setup
from tests.contract.test_document_review_journal import command
from tests.unit.test_source_sku_query import execution

pytestmark = pytest.mark.contract


def approved(dsn: str, tmp_path: Path, *, capability: bool = True, rows: str | None = None):
    journal, archive, p, content = (
        setup(dsn, tmp_path) if rows is None else setup(dsn, tmp_path, rows)
    )
    snapshot = archive.load(p.scope, p.snapshot_id)[1]
    sku = next(a for a in snapshot.assertions if a.predicate.value == "has_sku")
    task = journal.propose(
        replace(p, previous=sku, proposed_value="GPU-B"), AT + timedelta(seconds=2)
    )
    journal.decide(command(task), AT + timedelta(seconds=3))
    deps = bootstrap.build_dependency_store(dsn)
    deps.initialize()
    if capability:
        deps.initialize_corrections()
    return p, task, archive, content


def run_context(snapshot_id: str):
    return replace(
        execution(snapshot_id),
        workflow_name="reviewed-source-sku-query",
        started_at=AT + timedelta(seconds=5),
    )


def service(dsn: str):
    return bootstrap.build_reviewed_bom_query_service(dsn, clock=lambda: AT + timedelta(seconds=6))


def test_actual_reviewed_replay_keeps_original_and_retries_after_restart(
    archive_dsn: str, tmp_path: Path
):
    p, task, archive, content = approved(archive_dsn, tmp_path)
    (tmp_path / "source.xlsx").unlink()
    original = bootstrap.build_archived_bom_query_service(
        archive_dsn, clock=lambda: AT + timedelta(seconds=6)
    )
    first = original.execute(
        p.scope, p.snapshot_id, "original", execution(p.snapshot_id), context=context(p.scope)
    )
    result = service(archive_dsn).execute(
        p.scope,
        p.snapshot_id,
        "reviewed",
        (task.task_id,),
        AT + timedelta(seconds=4),
        run_context(p.snapshot_id),
        context=context(p.scope),
    )
    again = service(archive_dsn).execute(
        p.scope,
        p.snapshot_id,
        "reviewed",
        (task.task_id,),
        AT + timedelta(seconds=4),
        run_context(p.snapshot_id),
        context=context(p.scope),
    )
    assert result.as_dict() == again.as_dict()
    assert result.query.value == ("GPU-B",) and first.query.value == ("GPU-A",)
    assert (
        original.execute(
            p.scope, p.snapshot_id, "original", execution(p.snapshot_id), context=context(p.scope)
        ).as_dict()
        == first.as_dict()
    )
    assert archive.content(p.scope, p.snapshot_id) == content
    body = result.as_dict()
    assert (
        body["correction_selection"] == "explicit_selected_set"
        and body["unselected_reviews"] == "not_evaluated"
    )
    assert body["recomputation_executed"] is True and body["governing_state_updated"] is False
    with pytest.raises(DependencyConflictError):
        service(archive_dsn).execute(
            p.scope,
            p.snapshot_id,
            "reviewed",
            (task.task_id,),
            AT + timedelta(seconds=5),
            run_context(p.snapshot_id),
            context=context(p.scope),
        )
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (2,)


def test_reviewed_authorization_context_and_selection_fail_before_io():
    from procurement_intelligence_lab.application.reviewed_bom_queries import (
        ReviewedBomQueryService,
    )
    from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
        ReviewedSourceSkuQuery,
    )
    from procurement_intelligence_lab.platform.semantics.scope import StateScope

    scope = StateScope("synthetic", "p", "site", "1")
    ctx = context(scope)
    run = run_context("snapshot")
    s = ReviewedBomQueryService(
        cast(Any, NoIO()),
        cast(Any, NoIO()),
        cast(Any, NoIO()),
        ReviewedSourceSkuQuery,
        lambda: AT + timedelta(seconds=6),
    )
    with pytest.raises(ScopeAuthorizationError):
        s.execute(
            scope, "snapshot", "request", ("task",), AT, run, context=context(scope, review=False)
        )
    for ids, asof, execution_ctx in [
        ((), AT, run),
        (("task", "task"), AT, run),
        (cast(Any, ["task"]), AT, run),
        (("bad\ud800",), AT, run),
        (("task",), AT + timedelta(seconds=7), run),
        (("task",), AT, replace(run, code_revision="bad\ud800")),
    ]:
        with pytest.raises(SourceQueryContractError):
            s.execute(scope, "snapshot", "request", ids, asof, execution_ctx, context=ctx)


@pytest.mark.parametrize("mode", ["review", "context", "asof", "snapshot"])
def test_producer_cannot_substitute_retained_review_content(
    archive_dsn: str, tmp_path: Path, mode: str
):
    from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
        ReviewedSourceSkuQuery,
    )

    p, task, _, _ = approved(archive_dsn, tmp_path)
    s = service(archive_dsn)

    def substitute(
        snapshot: DocumentSnapshot,
        histories: tuple[ReviewHistory, ...],
        asof: datetime,
        provenance: DecisionProvenance,
    ):
        h = histories[0]
        assert h.decision is not None
        changed = replace(
            h,
            decision=replace(h.decision, command=replace(h.decision.command, reason="substituted")),
        )
        if mode == "review":
            histories = (changed,)
        elif mode == "context":
            provenance = replace(
                provenance, context=replace(provenance.context, code_revision="substituted")
            )
        elif mode == "asof":
            asof = AT + timedelta(seconds=3)
        elif mode == "snapshot":
            snapshot = replace(snapshot)
        return ReviewedSourceSkuQuery(snapshot, histories, asof, provenance)

    s = replace(s, producer=substitute)
    with pytest.raises(SourceQueryContractError):
        s.execute(
            p.scope,
            p.snapshot_id,
            "reviewed",
            (task.task_id,),
            AT + timedelta(seconds=4),
            run_context(p.snapshot_id),
            context=context(p.scope),
        )
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_clock_stamps_after_actual_reviewed_computation(archive_dsn: str, tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
        ReviewedSourceSkuQuery,
    )

    p, task, _, _ = approved(archive_dsn, tmp_path)
    recorded = [AT + timedelta(seconds=6)]

    def produce(
        snapshot: DocumentSnapshot,
        histories: tuple[ReviewHistory, ...],
        asof: datetime,
        provenance: DecisionProvenance,
    ):
        result = ReviewedSourceSkuQuery(snapshot, histories, asof, provenance)
        recorded[0] = AT + timedelta(seconds=7)
        return result

    s = replace(service(archive_dsn), clock=lambda: recorded[0], producer=produce)
    result = s.execute(
        p.scope,
        p.snapshot_id,
        "reviewed",
        (task.task_id,),
        AT + timedelta(seconds=4),
        run_context(p.snapshot_id),
        context=context(p.scope),
    )
    assert result.registration.recorded_at == AT + timedelta(seconds=7)
    impact = bootstrap.build_correction_impact_service(archive_dsn).inspect(
        p.scope,
        result.registration.snapshot_id,
        task.task_id,
        as_of=recorded[0],
        max_depth=2,
        context=context(p.scope),
    )
    assert result.query.reference_id in [a["reference_id"] for a in impact["affected"]]
    assert impact["recomputation_executed"] is False
    assert all(a["potentially_stale"] for a in impact["affected"])


def test_registration_cannot_substitute_equal_instant_metadata(archive_dsn: str, tmp_path: Path):
    from datetime import timezone

    from procurement_intelligence_lab.platform.semantics.dependencies import (
        DependencyManifest,
        DependencySnapshot,
    )

    p, task, _, _ = approved(archive_dsn, tmp_path)

    class SubstituteStore:
        def append(self, manifest: DependencyManifest, recorder_id: str, recorded_at: datetime):
            claim = manifest.claims[0]
            changed = replace(
                claim,
                event=replace(
                    claim.event,
                    provenance=replace(
                        claim.event.provenance,
                        context=replace(
                            claim.event.provenance.context,
                            started_at=claim.event.provenance.context.started_at.astimezone(
                                timezone(timedelta(hours=2))
                            ),
                        ),
                    ),
                ),
            )
            altered = replace(manifest, claims=(changed, *manifest.claims[1:]))
            assert altered == manifest and altered.digest != manifest.digest
            return DependencySnapshot(altered, recorder_id, recorded_at)

    s = replace(service(archive_dsn), dependencies=cast(Any, SubstituteStore()))
    with pytest.raises(SourceQueryContractError):
        s.execute(
            p.scope,
            p.snapshot_id,
            "reviewed",
            (task.task_id,),
            AT + timedelta(seconds=4),
            run_context(p.snapshot_id),
            context=context(p.scope),
        )
