"""Reject request drift, mutable inputs and false arrival evidence."""

from dataclasses import replace
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.processing.contracts import JobDefinition
from procurement_intelligence_lab.platform.processing.errors import JobContractError
from tests.local_prefix_job_fixtures import job_input


def test_job_identity_compares_full_request(tmp_path: Path) -> None:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    changed = replace(job, arrival=replace(job.arrival, expected_byte_length=0))
    assert changed.job_id == job.job_id
    assert changed.request_digest != job.request_digest
    assert replace(job, idempotency_key="another").job_id != job.job_id
    offset = job.arrival.announced_at.astimezone(timezone(timedelta(hours=1)))
    assert (
        replace(job, arrival=replace(job.arrival, announced_at=offset)).request_digest
        != job.request_digest
    )


def test_definition_derives_original_effective_context(tmp_path: Path) -> None:
    job, prepared, _ = job_input(tmp_path / "source.xlsx")
    assert canonical(job.definition.effective_context) == canonical(prepared.context)
    assert job.definition.manifest == prepared.manifest


@pytest.mark.parametrize("index", [0, -1])
def test_all_config_settings_rejected(tmp_path: Path, index: int) -> None:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    selections = list(job.definition.config.selections)
    selections[index] = replace(selections[index], settings=(("secret", "never-retain"),))
    with pytest.raises(JobContractError):
        replace(job.definition, config=replace(job.definition.config, selections=tuple(selections)))


@pytest.mark.parametrize("value", [True, -1, 1.5, None])
def test_arrival_rejects_invalid_length(tmp_path: Path, value: object) -> None:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    with pytest.raises(JobContractError):
        replace(job.arrival, expected_byte_length=value)


@pytest.mark.parametrize("key", ["", " x", "x ", "x" * 257, "\ud800"])
def test_job_keys_are_exact_bounded_unicode(tmp_path: Path, key: str) -> None:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    with pytest.raises(JobContractError):
        JobDefinition(job.arrival, key, job.definition)


def test_source_and_scope_cannot_be_substituted(tmp_path: Path) -> None:
    job, _, _ = job_input(tmp_path / "source.xlsx")
    with pytest.raises(JobContractError):
        replace(
            job,
            arrival=replace(
                job.arrival, source=replace(job.arrival.source, source_version="different")
            ),
        )
    with pytest.raises(JobContractError):
        replace(job.arrival, scope=replace(job.scope, project_id="foreign"))
