"""Validated six-stage publication and source-free, domain-checked recovery."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import NoReturn, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.application.archived_resolved_execution import (
    ResolvedExecutionArchiveReader,
)
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveUnavailableError,
    SemanticContractError,
)
from tests.bom_stage_fixtures import AT, HEADER
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_postgres_resolved_execution_archive import setup as storage
from tests.resolved_execution_fixtures import planned_resolved_inputs

pytestmark = pytest.mark.contract


def forbidden(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("unexpected source, runtime or factory access")


def setup(tmp_path: Path, dsn: str, *, rows: str | None = None, keys: tuple[str, ...] = ("GPU-A",)):
    m, r, c, q, path = (
        planned_resolved_inputs(tmp_path, keys=keys)
        if rows is None
        else planned_resolved_inputs(tmp_path, keys=keys, rows=rows)
    )
    service = bootstrap.build_planned_resolved_bom_archive_service(
        manifest=m,
        registry=r,
        config=c,
        normalization_policy=POLICY,
        resolution_policy=BomResolutionPolicy.from_parameters(q.policy.parameters),
        candidate_input=q.candidate_input,
        clock=lambda: AT + timedelta(seconds=1),
        archive_factory=lambda: bootstrap.build_resolved_execution_archive(dsn),
    )
    return service, q, path


def test_service_prepares_then_checks_ready_before_source_io(archive_dsn: str, tmp_path: Path):
    service, q, path = setup(tmp_path, archive_dsn)
    path.unlink()
    prefix = service.executions.prefix
    first = prefix.registry.implementations[0]
    bad = replace(
        prefix.registry,
        implementations=(
            replace(first, implementation_version="2"),
            *prefix.registry.implementations[1:],
        ),
    )
    with pytest.raises(SemanticContractError):
        replace(
            service,
            archive_factory=forbidden,
            executions=replace(service.executions, prefix=replace(prefix, registry=bad)),
        ).execute(q)
    with pytest.raises(ArchiveUnavailableError):
        service.execute(q)


def test_current_and_retained_receipts_remain_distinct(archive_dsn: str, tmp_path: Path):
    _, prefix_archive, _ = storage(archive_dsn)
    service, q, path = setup(tmp_path, archive_dsn)
    current = service.executions.execute(q)
    completed = CompletedResolvedPrefixSnapshot.from_execution(
        current.execution.receipt, service.policy_parameters
    )
    early = replace(
        completed.prefix,
        execution=replace(
            completed.prefix.execution, completed_at=AT + timedelta(microseconds=500000)
        ),
    )
    first_five = prefix_archive.append(early, path.read_bytes())
    first = service.execute(q)
    later = replace(
        service, executions=replace(service.executions, clock=lambda: AT + timedelta(seconds=2))
    ).execute(q)
    assert canonical(first.retained) == canonical(later.retained)
    assert later.retained.retained_prefix == first_five
    body = later.as_dict()
    assert (
        body["execution_receipt"]["receipt_digest"]
        != body["retained_execution_receipt"]["receipt_digest"]
    )
    assert (
        body["prefix_execution_receipt"]["receipt_digest"]
        != body["retained_prefix_execution_receipt"]["receipt_digest"]
    )
    assert (
        body["retained_prefix_execution_receipt"]["receipt_digest"]
        == first_five.completed.execution.receipt_digest
    )
    assert body["resolution"]["outcomes"][0]["matched_keys"] == ["GPU-A"]


@pytest.mark.parametrize("rows,keys", [(None, ("GPU-A",)), (None, ()), (HEADER, ())])
def test_source_free_reader_validates_recorded_policy_and_catalog(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rows: str | None,
    keys: tuple[str, ...],
):
    storage(archive_dsn)
    service, q, path = setup(tmp_path, archive_dsn, rows=rows, keys=keys)
    content = path.read_bytes()
    first = service.execute(q)
    path.unlink()
    monkeypatch.setattr(bootstrap, "build_planned_resolved_bom_service", forbidden)
    monkeypatch.setattr(type(service.executions), "prepare", forbidden)
    reader = bootstrap.build_resolved_execution_archive_reader(archive_dsn)
    scope, digest = first.retained.completed.scope, first.retained.receipt.execution_digest
    recovered = reader.show(scope, digest)
    assert canonical(recovered.retained) == canonical(first.retained)
    assert recovered.as_dict()["execution_receipt"] == first.as_dict()["retained_execution_receipt"]
    assert reader.history(scope).receipts == (first.retained.receipt,)
    assert reader.content(scope, digest) == content
    exported = cast(
        ArchivedResolvedPrefix,
        bootstrap.archive_codec().loads(reader.export(scope, digest).decode("utf-8")),
    )
    assert canonical(exported) == canonical(first.retained)
    assert exported.completed.execution.candidate_input.raw_json == q.candidate_input.raw_json


def test_reader_rehashed_matching_and_row_substitution_fail_closed(
    archive_dsn: str, tmp_path: Path
):
    storage(archive_dsn)
    service, q, _ = setup(tmp_path, archive_dsn)
    first = service.execute(q)
    scope, digest = first.retained.completed.scope, first.retained.receipt.execution_digest

    def invalid(completed: CompletedResolvedPrefixSnapshot) -> None:
        raise ValueError("private detail")

    reader = ResolvedExecutionArchiveReader(
        service.archive_factory(),
        invalid,
        lambda retained: bootstrap.archive_codec().dumps(retained).encode("utf-8"),
    )
    for read in (reader.show, reader.content, reader.export):
        with pytest.raises(ArchiveIntegrityError, match="validation") as exc:
            read(scope, digest)
        assert "private" not in str(exc.value)
    with pytest.raises(ArchiveIntegrityError):
        reader.history(scope)
    with pytest.raises(ArchiveContractError):
        replace(service, validate_completed=invalid).execute(q)


def test_pure_validator_checks_recorded_descriptor_and_policy(archive_dsn: str, tmp_path: Path):
    storage(archive_dsn)
    service, q, _ = setup(tmp_path, archive_dsn)
    completed = service.execute(q).retained.completed
    bootstrap.validate_completed_resolved_bom_prefix(completed)
    # An alternate normalization declaration can be structurally valid but unsupported.
    bad_prefix = replace(
        completed.prefix,
        snapshot=replace(
            completed.prefix.snapshot, normalization_policy_parameters=(("profile", "unsupported"),)
        ),
    )
    with pytest.raises(SemanticContractError):
        bootstrap.validate_completed_resolved_bom_prefix(replace(completed, prefix=bad_prefix))


@pytest.mark.parametrize("substitution", ["hidden_collision", "description_evidence"])
def test_reader_rejects_self_consistent_but_domain_wrong_graph(
    archive_dsn: str, tmp_path: Path, substitution: str
):
    from procurement_intelligence_lab.platform.execution.resolution_outputs import (
        MentionResolution,
        resolution_input_ids,
    )
    from tests.resolved_execution_fixtures import catalog

    storage(archive_dsn)
    service, q, path = setup(tmp_path, archive_dsn)
    original = service.executions.execute(q).execution.receipt
    candidate = (
        catalog(("GPU A", "GPU-A")) if substitution == "hidden_collision" else q.candidate_input
    )
    o = original.output
    p = replace(
        o.provenance,
        context=replace(
            o.provenance.context,
            input_snapshot_ids=tuple(
                dict.fromkeys(
                    (
                        *original.context.input_snapshot_ids,
                        *resolution_input_ids(o.previous, candidate.snapshot, o.policy),
                    )
                )
            ),
        ),
    )
    outcomes: list[MentionResolution] = []
    for outcome in o.outcomes:
        evidence = (
            outcome.decision.evidence
            if substitution == "hidden_collision"
            else (
                next(
                    a for a in outcome.mention.assertions if a.predicate.value == "has_description"
                ),
            )
        )
        outcomes.append(
            replace(
                outcome,
                candidate_snapshot_id=candidate.snapshot.snapshot_id,
                decision=replace(outcome.decision, provenance=p, evidence=evidence),
            )
        )
    decisions = {x.mention.assertions[0].subject_key: x.decision for x in outcomes}
    output = replace(
        o,
        candidates=candidate.snapshot,
        provenance=p,
        outcomes=tuple(outcomes),
        canonicalized=tuple(
            replace(c, resolution=decisions[c.assertion.subject_key]) for c in o.canonicalized
        ),
    )
    entry = replace(
        original.entries[5],
        input_ids=output.input_ids,
        output_ids=output.reference_ids,
        event_id=output.event.event_id,
    )
    forged = replace(
        original,
        candidate_input=candidate,
        output=output,
        entries=(*original.entries[:5], entry, *original.entries[6:]),
    )
    completed = CompletedResolvedPrefixSnapshot.from_execution(forged, service.policy_parameters)
    # The technology-neutral archive accepts a coherent graph. Procurement policy rejects it.
    service.archive_factory().append(completed, path.read_bytes())
    reader = bootstrap.build_resolved_execution_archive_reader(archive_dsn)
    for read in (reader.show, reader.content, reader.export):
        with pytest.raises(ArchiveIntegrityError):
            read(completed.scope, completed.execution_digest)
