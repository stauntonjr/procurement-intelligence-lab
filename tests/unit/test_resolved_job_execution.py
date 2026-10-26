"""Actual six-stage execution guard and admission before persistence construction."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.package_document_executors import StructureExecutor
from procurement_intelligence_lab.platform.execution.resolution_runner import run_resolved_prefix
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobContractError,
)
from tests.local_prefix_job_fixtures import NOW
from tests.resolved_job_fixtures import job_input


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("persistence/source-dependent runtime must not be constructed")


def test_guard_observes_one_actual_capture_before_structure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    job, p, _ = job_input(tmp_path)
    captures: list[str] = []
    monkeypatch.setattr(StructureExecutor, "invoke", forbidden)

    def guard(captured: Any):
        captures.append(captured.artifact.content_hash)
        raise ResolvedJobContractError("declared byte mismatch")

    with pytest.raises(ResolvedJobContractError):
        run_resolved_prefix(p, clock=lambda: NOW, capture_guard=guard)
    assert captures == [job.arrival.expected_content_hash]


def test_guard_success_keeps_six_actual_stages(tmp_path: Path):
    _, p, _ = job_input(tmp_path)
    seen: list[str] = []
    done = run_resolved_prefix(
        p, clock=lambda: NOW, capture_guard=lambda c: seen.append(c.artifact.artifact_id)
    )
    assert len(seen) == 1
    assert [e.status.value for e in done.receipt.entries] == ["SUCCEEDED"] * 6 + [
        "NOT_EXECUTED"
    ] * 6
    assert not done.receipt.package_execution_complete


def test_pinned_preparation_does_not_construct_persistence_and_rejects_unsupported_recipe(
    tmp_path: Path,
):
    job, p, _ = job_input(tmp_path)
    service = bootstrap.build_resolved_prefix_job_service(
        clock=lambda: NOW, journal_factory=forbidden
    )
    prepared = service.prepare_stored(job.definition)
    assert prepared.request == p.request
    bad_definition = replace(
        job.definition,
        recipe_id="unsupported",
        prefix=replace(job.definition.prefix, recipe_id="unsupported"),
    )
    with pytest.raises(ResolvedJobContractError):
        service.submit(replace(job, definition=bad_definition))


def test_preparation_rejects_unrecognized_pinned_implementation_before_storage(tmp_path: Path):
    job, _, _ = job_input(tmp_path)
    service = bootstrap.build_resolved_prefix_job_service(
        clock=lambda: NOW, journal_factory=forbidden
    )
    # Metadata remains internally consistent, but unsupported by the explicit local recipe.
    prefix = job.definition.prefix
    entries = list(prefix.registry.implementations)
    from procurement_intelligence_lab.platform.planning.planner import plan_manifest

    old = entries[0]
    entries[0] = replace(old, implementation_version="unsupported-version")
    registry = replace(prefix.registry, implementations=tuple(entries))
    plan = plan_manifest(prefix.manifest, registry=registry, config=prefix.config)
    bad = replace(
        job,
        definition=replace(job.definition, prefix=replace(prefix, registry=registry, plan=plan)),
    )
    with pytest.raises(ResolvedJobContractError):
        service.submit(bad)
