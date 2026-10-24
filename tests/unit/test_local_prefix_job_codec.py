"""Retained jobs are portable typed evidence, never callbacks or unchecked JSON."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.semantic_codec import canonical, digest
from procurement_intelligence_lab.platform.execution.identity import canonical as exact
from procurement_intelligence_lab.platform.processing.contracts import (
    JobJournalReceipt,
    JobView,
    StartAttemptCommand,
    StartIntent,
)
from procurement_intelligence_lab.platform.processing.lifecycle import (
    start_transition,
    submission_transition,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
)
from tests.local_prefix_job_fixtures import NOW, job_input
from tests.unit.test_planned_execution_archive_codec import (
    test_old_snapshot_wire_is_literal_unchanged,
)


def test_actual_pinned_definition_and_terminal_receipt_round_trip(tmp_path: Path):
    job, prepared, _ = job_input(tmp_path / "source.xlsx")
    codec = bootstrap.archive_codec()
    view = JobView(job, JobJournalReceipt(submission_transition(job, now=NOW)))
    command = StartAttemptCommand(job.scope, job.job_id, "start", "developer", 1, StartIntent.FIRST)
    started = start_transition(view, command, now=NOW)
    from procurement_intelligence_lab.platform.execution.archive import (
        CompletedPrefixSnapshot,
        ExecutionArchiveReceipt,
    )
    from procurement_intelligence_lab.platform.execution.runner import run_prefix
    from procurement_intelligence_lab.platform.processing.contracts import AttemptSuccess
    from procurement_intelligence_lab.platform.processing.lifecycle import success_transition
    from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt

    current = run_prefix(prepared, clock=lambda: NOW).receipt
    completed = CompletedPrefixSnapshot.from_execution(
        current, job.definition.normalization_parameters
    )
    snapshot = completed.snapshot
    source_receipt = ArchiveReceipt(
        1,
        snapshot.snapshot_id,
        job.scope,
        snapshot.artifact.artifact_id,
        snapshot.artifact.content_hash,
        len(snapshot.assertions),
        snapshot.origin.recorded_at,
    )
    retained = ExecutionArchiveReceipt(
        1, current.execution_digest, current.receipt_digest, source_receipt
    )
    assert started.attempt is not None
    terminal = success_transition(
        JobView(job, JobJournalReceipt(started)),
        started.attempt,
        AttemptSuccess(completed, retained),
        now=NOW,
    )
    for value in (job, view, command, started, JobJournalReceipt(started), terminal):
        loaded = codec.loads(codec.dumps(value))
        assert exact(loaded) == exact(value)
    assert (
        codec.loads(codec.dumps(job)).definition.plan.canonical_json
        == job.definition.plan.canonical_json
    )
    test_old_snapshot_wire_is_literal_unchanged()


def rehash(graph: dict[str, Any]) -> str:
    records = graph["records"]
    rebuilt = {}

    def walk(value: Any) -> Any:
        if not isinstance(value, list):
            return value
        if value and value[0] == "ref":
            node = records[value[1]]
            node = {"kind": node["kind"], "fields": [[k, walk(v)] for k, v in node["fields"]]}
            key = digest(node)
            rebuilt[key] = node
            return ["ref", key]
        return [walk(x) for x in cast(list[Any], value)]

    graph["root"] = walk(graph["root"])
    graph["records"] = rebuilt
    return canonical(graph)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("JobDefinition", "idempotency_key", ["str", " bad"]),
        ("ArtifactArrival", "expected_byte_length", ["bool", True]),
        ("JobTransition", "version", ["int", 3]),
        (
            "StageSelection",
            "settings",
            ["tuple", [["tuple", [["str", "secret"], ["str", "secret-value"]]]]],
        ),
    ],
)
def test_all_journal_roots_reject_malformed_linkage(
    tmp_path: Path, target: str, field: str, value: Any
):
    job, _, _ = job_input(tmp_path / "source.xlsx")
    codec = bootstrap.archive_codec()
    root = JobView(job, JobJournalReceipt(submission_transition(job, now=NOW)))
    graph = json.loads(codec.dumps(root))
    for node in graph["records"].values():
        if node["kind"] == target:
            node["fields"] = [[k, value if k == field else v] for k, v in node["fields"]]
            break
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(rehash(graph))


def test_unregistered_execution_authority_and_excessive_depth_rejected(tmp_path: Path):
    _, prepared, _ = job_input(tmp_path / "source.xlsx")
    codec = bootstrap.archive_codec()
    with pytest.raises(ArchiveContractError):
        codec.dumps(prepared)
    nested: object = "leaf"
    for _ in range(66):
        nested = (nested,)
    with pytest.raises(ArchiveContractError):
        codec.dumps(nested)
