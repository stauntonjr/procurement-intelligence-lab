"""Strict synthetic authority declarations never infer missing approval."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    BomAuthorityInput,
    BomReconciliationPolicy,
    load_bom_authority,
)
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from tests.reconciliation_fixtures import metadata, policy, producer


def test_authority_wire_exact_fields_nulls_and_bounds(tmp_path: Path):
    p, _ = producer(tmp_path)
    wire = metadata((p,), approval=None)
    raw = json.dumps(wire).encode()
    got = load_bom_authority(raw)
    assert got.records[0].approved_at is None
    assert (
        load_bom_authority(b" " * (65536 - len(raw)) + raw).evidence.semantic_digest
        == got.evidence.semantic_digest
    )
    invalid: list[Any] = [
        {},
        dict(wire, extra=1),
        dict(wire, producers=[]),
        dict(wire, producers=wire["producers"] * 9),
    ]
    for key in wire["producers"][0]:
        rec = dict(wire["producers"][0])
        del rec[key]
        invalid.append(dict(wire, producers=[rec]))
    bad_changes: list[dict[str, Any]] = [
        {"approval": {}},
        {"approval": {"record_ref": "", "approved_at": "bad"}},
        {"revision_id": "x" * 257},
        {"supersedes_revision_ids": ["revision-0"]},
        {"source_role": "model"},
        {"document_at": "2026-10-19"},
        {"extra": "x"},
    ]
    for changes in bad_changes:
        invalid.append(dict(wire, producers=[dict(wire["producers"][0], **changes)]))
    for value in invalid:
        with pytest.raises(PackageExecutionError):
            load_bom_authority(json.dumps(value).encode())
    for data in [
        b" " * (65537 - len(raw)) + raw,
        b'{"schema_version":"1.0","schema_version":"1.0"}',
        b'{"a":NaN}',
        b"\xff",
        b'{"a":"\\ud800"}',
        ("[" * 18 + "0" + "]" * 18).encode(),
    ]:
        with pytest.raises(PackageExecutionError):
            load_bom_authority(data)
    with pytest.raises(PackageExecutionError):
        BomAuthorityInput(replace(got.evidence, semantic_json=b"{}"), got.records)
    assert BomReconciliationPolicy(policy()).evidence == policy()
    with pytest.raises(PackageExecutionError):
        replace(got.records[0], approval_record_ref="x", approved_at=None)


def test_canonical_order_and_offset_audit(tmp_path: Path):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two")
    wire = metadata((p, q))
    a = load_bom_authority(json.dumps(wire).encode())
    wire["producers"].reverse()
    b = load_bom_authority(json.dumps(wire, indent=2).encode())
    assert a.evidence.semantic_json == b.evidence.semantic_json
    assert a.evidence.raw_sha256 != b.evidence.raw_sha256


def test_eight_records_are_valid_but_duplicate_revisions_are_not(tmp_path: Path):
    p, _ = producer(tmp_path)
    wire = metadata((p,))
    base = wire["producers"][0]
    wire["producers"] = [
        dict(base, execution_digest=f"{i:064x}", revision_id=f"rev-{i}") for i in range(8)
    ]
    assert len(load_bom_authority(json.dumps(wire).encode()).records) == 8
    wire["producers"][1]["revision_id"] = "rev-0"
    with pytest.raises(PackageExecutionError):
        load_bom_authority(json.dumps(wire).encode())


def test_required_authority_times_cannot_be_null_in_direct_construction(tmp_path: Path):
    p, _ = producer(tmp_path)
    r = load_bom_authority(json.dumps(metadata((p,))).encode()).records[0]
    from typing import cast

    for key in ("effective_from", "document_at"):
        with pytest.raises(PackageExecutionError):
            replace(r, **{key: cast(Any, None)})
