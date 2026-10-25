"""Additive finite persistence roots keep existing graph encoding unchanged."""

from pathlib import Path

import pytest

from procurement_intelligence_lab.bootstrap import archive_codec
from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
    ArchivedReconciliation,
    CompletedReconciliationSnapshot,
    ReconciliationArchiveReceipt,
)
from tests.reconciliation_fixtures import empty_receipt


def test_new_graph_roundtrip_and_legacy_encoding(tmp_path: Path):
    r = empty_receipt(tmp_path)
    c = CompletedReconciliationSnapshot(r)
    codec = archive_codec()
    encoded = codec.dumps(c)
    assert codec.dumps(codec.loads(encoded)) == encoded
    legacy = codec.dumps(r.output.inputs.recorded_producers[0])
    assert codec.dumps(codec.loads(legacy)) == legacy
    receipt = ReconciliationArchiveReceipt(
        c.scope,
        1,
        c.execution_digest,
        r.receipt_digest,
        tuple(p.receipt for p in r.output.inputs.recorded_producers),
    )
    archived = ArchivedReconciliation(c, receipt)
    assert codec.loads(codec.dumps(archived)) == archived


def test_finite_roots_and_existing_bounds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import pytest

    from procurement_intelligence_lab.adapters import semantic_codec
    from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
        RetainedReconciliationRequest,
    )
    from procurement_intelligence_lab.platform.semantics.errors import (
        ArchiveContractError,
        ArchiveIntegrityError,
    )

    r = empty_receipt(tmp_path)
    codec = archive_codec()
    c = CompletedReconciliationSnapshot(r)
    with pytest.raises(ArchiveContractError):
        codec.dumps(RetainedReconciliationRequest(r.output.inputs, r.context))
    raw = codec.dumps(c)
    assert (
        semantic_codec.MAX_PAYLOAD_BYTES == 16 * 1024 * 1024 and semantic_codec.MAX_NODES == 50000
    )
    monkeypatch.setattr(semantic_codec, "MAX_PAYLOAD_BYTES", len(raw.encode()) - 1)
    with pytest.raises(ArchiveContractError):
        codec.dumps(c)
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(raw)


def test_history_rejects_boolean_cursor(tmp_path: Path):
    import pytest

    from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
        ReconciliationHistoryPage,
    )
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    r = empty_receipt(tmp_path)
    c = CompletedReconciliationSnapshot(r)
    receipt = ReconciliationArchiveReceipt(
        c.scope,
        1,
        c.execution_digest,
        r.receipt_digest,
        tuple(p.receipt for p in r.output.inputs.recorded_producers),
    )
    with pytest.raises(ArchiveContractError):
        ReconciliationHistoryPage(c.scope, 0, 1, (receipt,), True, True)
