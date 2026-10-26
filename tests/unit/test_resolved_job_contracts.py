"""A different catalog, scope or sixth-stage selection must never masquerade as replay."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.execution.resolution_inputs import load_candidate_input
from procurement_intelligence_lab.platform.processing.resolved_binding import validate_completion
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobContractError,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from tests.resolved_job_fixtures import completed, job_input


def test_request_pins_raw_catalog_even_when_semantic_identity_is_equal(tmp_path: Path):
    job, p, raw = job_input(tmp_path)
    original = job.definition.candidate_input
    changed_input = load_candidate_input(
        json.dumps(json.loads(original.raw_json), indent=2).encode()
    )
    assert changed_input.snapshot.snapshot_id == original.snapshot.snapshot_id
    changed = replace(job, definition=replace(job.definition, candidate_input=changed_input))
    assert changed.job_id == job.job_id
    assert changed.request_digest != job.request_digest
    done = completed(job, p)
    validate_completion(job, done, raw)
    with pytest.raises(ResolvedJobContractError):
        validate_completion(changed, done, raw)


def test_new_namespaces_and_exact_source_binding(tmp_path: Path):
    job, _, _ = job_input(tmp_path)
    assert job.job_id.startswith("local-resolved-prefix-job-v1:")
    assert replace(job, idempotency_key="other").job_id != job.job_id
    with pytest.raises(ResolvedJobContractError):
        replace(
            job,
            arrival=replace(
                job.arrival, source=replace(job.arrival.source, source_version="other")
            ),
        )


@pytest.mark.parametrize(
    "change", ["scope", "future", "metadata", "policy", "settings", "environment"]
)
def test_pinned_definition_rejects_invalid_direct_construction(tmp_path: Path, change: str):
    job, _, _ = job_input(tmp_path)
    d = job.definition
    with pytest.raises(SemanticContractError):
        if change in ("scope", "future"):
            wire = json.loads(d.candidate_input.raw_json)
            if change == "scope":
                wire["scope"]["project_id"] = "foreign"
            else:
                wire["effective_at"] = (
                    d.prefix.request.captured_at + timedelta(days=1)
                ).isoformat()
            replace(d, candidate_input=load_candidate_input(json.dumps(wire).encode()))
        elif change == "metadata":
            replace(d, resolution_metadata=replace(d.resolution_metadata, policy_version="wrong"))
        elif change == "policy":
            replace(d, policy=replace(d.policy, identifier_namespace="foreign"))
        elif change == "environment":
            q = d.prefix.request
            replace(
                d,
                prefix=replace(
                    d.prefix,
                    request=replace(
                        q, context=replace(q.context, environment=(("secret", "not-retained"),))
                    ),
                ),
            )
        else:
            selections = list(d.prefix.config.selections)
            selections[-1] = replace(selections[-1], settings=(("secret", "not-retained"),))
            replace(
                d,
                prefix=replace(
                    d.prefix, config=replace(d.prefix.config, selections=tuple(selections))
                ),
            )


@pytest.mark.parametrize("value", ["", " x", "x ", "x" * 257, "\ud800"])
def test_bounded_job_keys(tmp_path: Path, value: str):
    job, _, _ = job_input(tmp_path)
    with pytest.raises(ResolvedJobContractError):
        replace(job, idempotency_key=value)


def test_completion_rejects_raw_source_and_pinned_sixth_metadata_substitution(tmp_path: Path):
    job, p, raw = job_input(tmp_path)
    done = completed(job, p)
    with pytest.raises(ResolvedJobContractError):
        validate_completion(job, done, raw + b"other")
    assert canonical(job.definition.prefix.effective_context) == canonical(p.prefix.context)
