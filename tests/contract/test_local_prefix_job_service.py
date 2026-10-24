"""Actual five-stage execution with durable claims, pinned inputs and truthful failures."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.package_document_executors import (
    CaptureExecutor,
    StructureExecutor,
)
from procurement_intelligence_lab.platform.processing.contracts import JobStatus, StartIntent
from procurement_intelligence_lab.platform.processing.errors import (
    JobBusyError,
    JobContractError,
    JobUnavailableError,
)
from tests.contract.test_postgres_local_prefix_jobs import first, ready
from tests.local_prefix_job_fixtures import NOW, job_input


def test_real_execution_and_source_config_free_recovery(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, content = job_input(tmp_path / "source.xlsx")
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    receipt = service.execute(first(job)).receipt
    assert receipt.transition.status is JobStatus.SUCCEEDED
    assert receipt.transition.success is not None
    current = receipt.transition.success.completed.execution
    assert len(current.entries) == 12 and len(current.output.chain) == 5
    (tmp_path / "source.xlsx").unlink()
    reader = bootstrap.build_local_prefix_job_reader(archive_dsn)
    assert (
        reader.result(job.scope, job.job_id).completed.execution.receipt_digest
        == current.receipt_digest
    )
    assert reader.content(job.scope, job.job_id) == content

    def forbidden(_: Any) -> Any:
        raise AssertionError("replay must not prepare current runtime")

    replay_service = replace(service, prepare_stored=forbidden)
    assert replay_service.execute(first(job)).receipt == receipt


def test_changed_source_fails_immediately_after_capture(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    jobs = ready(archive_dsn)
    job, _, content = job_input(tmp_path / "source.xlsx")
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    (tmp_path / "source.xlsx").write_bytes(content + b"changed")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("structure must not run on mismatched bytes")

    monkeypatch.setattr(StructureExecutor, "invoke", forbidden)
    from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError

    with pytest.raises(SemanticContractError) as failure:
        service.execute(first(job))
    assert failure.value.as_dict()["code"] == "pil.input.local_prefix_job_invalid"
    failed = jobs.load(job.scope, job.job_id)
    assert failed.status is JobStatus.FAILED
    assert failed.latest.transition.failure is not None
    assert failed.latest.transition.failure.code.value == "pil.input.local_prefix_job_invalid"
    (tmp_path / "source.xlsx").write_bytes(content)
    monkeypatch.undo()
    retry = service.execute(first(job, "retry", 3, StartIntent.RETRY)).receipt
    assert retry.transition.success is not None
    assert retry.transition.success.completed.execution.context == job.definition.effective_context


def test_submit_and_replayed_start_never_capture(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no source invocation allowed")

    monkeypatch.setattr(CaptureExecutor, "invoke", forbidden)
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    jobs.start(first(job), now=NOW)
    with pytest.raises(JobBusyError):
        service.execute(first(job))
    assert jobs.load(job.scope, job.job_id).status is JobStatus.RUNNING


def test_unsupported_stored_recipe_does_not_claim(archive_dsn: str, tmp_path: Path):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    bad = replace(job, definition=replace(job.definition, recipe_id="unsupported-recipe"))
    jobs.submit(bad, now=NOW)
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    with pytest.raises(JobContractError):
        service.execute(first(bad))
    assert jobs.load(job.scope, job.job_id).status is JobStatus.SUBMITTED


def test_prepublication_failure_is_safe_and_publication_ambiguity_is_not_failed(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    original = jobs.complete

    def committed_then_raise(*args: Any, **kwargs: Any) -> Any:
        original(*args, **kwargs)
        raise JobUnavailableError("lost acknowledgement")

    monkeypatch.setattr(jobs, "complete", committed_then_raise)
    with pytest.raises(JobUnavailableError):
        service.execute(first(job))
    assert jobs.load(job.scope, job.job_id).status is JobStatus.SUCCEEDED
    other = replace(job, idempotency_key="other")
    service.submit(other)

    def private_error(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("postgresql://private-secret source contents")

    monkeypatch.setattr(CaptureExecutor, "invoke", private_error)
    with pytest.raises(JobUnavailableError) as exc:
        service.execute(first(other))
    assert "private-secret" not in str(exc.value)
    failed = jobs.load(other.scope, other.job_id)
    assert failed.status is JobStatus.FAILED and failed.latest.transition.failure is not None
    assert failed.latest.transition.failure.diagnostic == "infrastructure_failure"


@pytest.mark.parametrize("quantity", ["0.5", "0", "-2", None])
def test_job_path_preserves_fractional_zero_negative_and_unresolved(
    archive_dsn: str, tmp_path: Path, quantity: str | None
):
    from decimal import Decimal

    from tests.bom_stage_fixtures import HEADER, ROW

    rows = HEADER + (
        ROW.replace("<v>0.5</v>", f"<v>{quantity}</v>")
        if quantity is not None
        else ROW.replace('<c r="C7"><v>0.5</v></c>', "")
    )
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx", rows=rows)
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    receipt = service.execute(first(job)).receipt
    assert receipt.transition.success is not None
    observations = receipt.transition.success.completed.snapshot.observations
    observed = [o.value for o in observations if o.source_field.field_name == "quantity"]
    assert observed == [Decimal(quantity) if quantity is not None else None]


def test_failure_journal_outage_leaves_running_unresolved(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    (tmp_path / "source.xlsx").unlink()

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise JobUnavailableError("journal unavailable")

    monkeypatch.setattr(jobs, "fail", unavailable)
    with pytest.raises(JobUnavailableError):
        service.execute(first(job))
    assert jobs.load(job.scope, job.job_id).status is JobStatus.RUNNING


@pytest.mark.parametrize("empty", [True, False])
def test_empty_and_duplicate_rows_keep_their_source_meaning(
    archive_dsn: str, tmp_path: Path, empty: bool
):
    from decimal import Decimal

    from tests.bom_stage_fixtures import HEADER, ROW

    rows = HEADER if empty else HEADER + ROW + ROW.replace("7", "8")
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx", rows=rows)
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    receipt = service.execute(first(job)).receipt
    assert receipt.transition.success is not None
    snapshot = receipt.transition.success.completed.snapshot
    assert [o.value for o in snapshot.observations if o.source_field.field_name == "quantity"] == (
        [] if empty else [Decimal("0.5"), Decimal("0.5")]
    )
    assert len(snapshot.mentions) == (0 if empty else 2)


def test_stored_alternate_units_and_currency_are_reconstructed(archive_dsn: str, tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.normalization import (
        BomNormalizationPolicy,
        CountUnit,
    )

    jobs = ready(archive_dsn)
    job, _, _ = job_input(
        tmp_path / "source.xlsx",
        policy=BomNormalizationPolicy(CountUnit.DOZEN, "GBP", CountUnit.DOZEN),
    )
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    receipt = service.execute(first(job)).receipt
    assert receipt.transition.success is not None
    observations = receipt.transition.success.completed.snapshot.observations
    quantity = next(o for o in observations if o.source_field.field_name == "quantity")
    price = next(o for o in observations if o.source_field.field_name == "unit_price")
    assert str(quantity.value) == "6.0" and quantity.unit == "each"
    assert str(price.value) == "100.50" and price.unit == "GBP/dozen"


def test_command_acknowledgement_separates_historical_replay_from_new_execution(
    archive_dsn: str, tmp_path: Path
):
    jobs = ready(archive_dsn)
    job, _, _ = job_input(tmp_path / "source.xlsx")
    service = bootstrap.build_local_prefix_job_service(
        clock=lambda: NOW, journal_factory=lambda: jobs
    )
    service.submit(job)
    fresh = service.execute(first(job))
    replayed = service.execute(first(job))
    assert not fresh.historical and replayed.historical
    assert fresh.command_receipt == replayed.command_receipt
    assert fresh.command_receipt.transition.version == 2
    assert fresh.receipt == replayed.receipt
    assert fresh.observed_version == replayed.observed_version == 3
