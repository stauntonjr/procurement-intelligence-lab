"""Publication and recovery enforce domain semantics without current source/runtime files."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.application.archived_reconciliation import (
    ArchivedReconciliationService,
)
from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    ArchivedReconciliation,
    CompletedReconciliationSnapshot,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconciliationOperationReceipt,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveIntegrityError,
    ArchiveUnavailableError,
    PackageExecutionContractError,
)
from tests.bom_stage_fixtures import AT, SCOPE
from tests.contract.test_postgres_reconciliation_archive import setup
from tests.contract.test_reconciliation_operation import forbidden, service

pytestmark = pytest.mark.contract


def test_archive_readiness_precedes_current_executor(archive_dsn: str, tmp_path: Path):
    s, args, _ = service(tmp_path)
    s = replace(s, producer_reader_factory=forbidden, executor_factory=forbidden)
    archived = ArchivedReconciliationService(
        s,
        lambda: bootstrap.build_reconciliation_archive(archive_dsn),
        bootstrap.validate_completed_reconciliation,
    )
    with pytest.raises(ArchiveUnavailableError):
        archived.execute(**args)


def test_current_historical_first_retained_are_distinct(archive_dsn: str, tmp_path: Path):
    archive, c, _ = setup(archive_dsn, tmp_path)
    first = archive.append(c)
    from procurement_intelligence_lab.application.archived_reconciliation import (
        RetainedReconciliationResult,
    )

    later = replace(c.execution, completed_at=AT + timedelta(seconds=9))
    body = RetainedReconciliationResult(later, first).as_dict()
    assert sum(e["status"] == "SUCCEEDED" for e in body["current_operation"]["entries"]) == 1
    assert (
        sum(
            e["status"] == "SUCCEEDED"
            for e in body["recorded_producers"][0]["execution_receipt"]["entries"]
        )
        == 6
    )
    assert (
        body["current_operation"]["receipt_digest"]
        != body["first_retained_operation"]["receipt_digest"]
    )


def test_source_free_reader_requires_no_files_or_executors(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    archive, c, _ = setup(archive_dsn, tmp_path)
    archive.append(c)
    for path in tmp_path.rglob("*.xlsx"):
        path.unlink()
    monkeypatch.setattr(bootstrap, "build_planned_bom_service", forbidden)
    monkeypatch.setattr(bootstrap, "build_planned_resolved_bom_service", forbidden)
    reader = bootstrap.build_reconciliation_archive_reader(archive_dsn)
    got = reader.show(c.scope, c.execution_digest).as_dict()
    assert got["current_operation"]["states"][0]["attributes"][0]["value"] == "0.5"
    assert len(reader.history(SCOPE).receipts) == 1


def test_resealed_authority_and_state_fail_pure_validation(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    archive, c, _ = setup(archive_dsn, tmp_path)
    retained = archive.append(c)
    o = c.execution.output
    s = o.states[0]
    o = replace(o, states=(replace(s, attributes=(replace(s.attributes[0], value=Decimal(99)),)),))
    entries = list(c.execution.entries)
    entries[6] = replace(entries[6], output_ids=o.reference_ids, event_id=o.event.event_id)
    forged = CompletedReconciliationSnapshot(replace(c.execution, output=o, entries=tuple(entries)))
    with pytest.raises(PackageExecutionContractError):
        bootstrap.validate_completed_reconciliation(forged)
    row = ArchivedReconciliation(
        forged,
        replace(
            retained.receipt,
            execution_digest=forged.execution_digest,
            retained_receipt_digest=forged.execution.receipt_digest,
        ),
    )
    reader = bootstrap.build_reconciliation_archive_reader(archive_dsn)

    def loaded(scope: object, execution_digest: str):
        return row

    monkeypatch.setattr(reader.archive, "load", loaded)
    with pytest.raises(ArchiveIntegrityError):
        reader.show(SCOPE, forged.execution_digest)


def test_export_references_all_original_sources(archive_dsn: str, tmp_path: Path):
    archive, c, p = setup(archive_dsn, tmp_path)
    archive.append(c)
    reader = bootstrap.build_reconciliation_archive_reader(archive_dsn)
    content = cast(dict[str, Any], reader.content_manifest(SCOPE, c.execution_digest))
    assert content["schema"] == "reconciliation-content-manifest/v1"
    assert content["producers"][0]["execution_digest"] == p.completed.execution_digest
    assert (
        "original_source_bytes_included" in content
        and content["original_source_bytes_included"] is False
    )
    assert (
        bootstrap.archive_codec().loads(reader.export(SCOPE, c.execution_digest).decode()).completed
        == c
    )


def test_nonappend_result_bound_is_invoked_contract_failure(tmp_path: Path):
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    s, args, calls = service(tmp_path)

    def invalid(receipt: ReconciliationOperationReceipt):
        raise ArchiveContractError("injected finite-codec bound")

    with pytest.raises(PackageExecutionContractError):
        replace(s, validate_receipt=invalid).execute(**args)
    assert len(calls) == 1


def test_archived_export_bound_rolls_back(
    archive_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.platform.semantics.errors import (
        ArchiveContractError,
        ArchiveNotFoundError,
    )

    archive, c, _ = setup(archive_dsn, tmp_path)
    original = archive.codec.dumps

    def limited(value: object):
        if isinstance(value, ArchivedReconciliation):
            raise ArchiveContractError("injected whole-export bound")
        return original(value)

    monkeypatch.setattr(archive.codec, "dumps", limited)
    with pytest.raises(ArchiveContractError):
        archive.append(c)
    with pytest.raises(ArchiveNotFoundError):
        archive.load(c.scope, c.execution_digest)
