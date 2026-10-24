"""Strict input tests detect silent defaulting, identity loss and malformed catalogs."""

import json
from dataclasses import replace
from datetime import timedelta, timezone
from typing import Any

import pytest

from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateInputEvidence,
    load_candidate_input,
)
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from tests.resolved_execution_fixtures import catalog, catalog_wire, policy_evidence


def test_catalog_semantic_identity_ignores_order_and_format():
    first = catalog(("GPU-A", "CPU-A"))
    raw = json.dumps(catalog_wire(("CPU-A", "GPU-A")), indent=2).encode()
    second = load_candidate_input(raw)
    assert first.snapshot.keys == ("CPU-A", "GPU-A")
    assert first.snapshot.snapshot_id == second.snapshot.snapshot_id
    assert first.raw_sha256 != second.raw_sha256
    assert second.raw_json == raw
    assert catalog(()).snapshot.keys == ()
    assert catalog((" GPU-A ",)).snapshot.keys == (" GPU-A ",)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": "2"},
        {"keys": None},
        {"keys": [True]},
        {"keys": [0]},
        {"keys": [""]},
        {"keys": ["   "]},
        {"keys": ["X" * 257]},
        {"keys": ["A", "A"]},
        {"keys": [str(i) for i in range(257)]},
        {"keys": ["\ud800"]},
        {"catalog_id": False},
        {"unknown": "field"},
        {"scope": {"tenant_id": "x"}},
        {"effective_at": "2026-10-19"},
    ],
)
def test_catalog_wire_bounds_and_exact_types(changes: dict[str, Any]):
    raw = json.dumps(catalog_wire(**changes)).encode()
    with pytest.raises(PackageExecutionError):
        load_candidate_input(raw)


@pytest.mark.parametrize(
    "raw",
    [
        b"null",
        b"[]",
        b"",
        b"\xff",
        b'{"x":NaN}',
        b'{"schema_version":"1.0","schema_version":"1.0"}',
    ],
)
def test_missing_or_ambiguous_wire_never_becomes_empty_catalog(raw: bytes):
    with pytest.raises(PackageExecutionError):
        load_candidate_input(raw)


def test_exact_input_bounds():
    assert len(catalog(tuple(str(i) for i in range(256))).snapshot.keys) == 256
    assert catalog(("X" * 256,)).snapshot.keys == ("X" * 256,)
    raw = json.dumps(catalog_wire()).encode()
    assert load_candidate_input(raw + b" " * (32768 - len(raw))).snapshot.keys == ("GPU-A",)
    with pytest.raises(PackageExecutionError):
        load_candidate_input(raw + b" " * (32769 - len(raw)))


def test_catalog_raw_bytes_must_match_snapshot():
    first, other = catalog(), catalog(("CPU-A",))
    with pytest.raises(PackageExecutionError):
        CandidateInputEvidence(first.snapshot, other.raw_json)
    with pytest.raises(PackageExecutionError):
        replace(first.snapshot, keys=["GPU-A"])
    with pytest.raises(PackageExecutionError):
        replace(first.snapshot, keys=("Z", "A"))


def test_equal_instants_keep_offset_identity():
    first = catalog()
    other = catalog(
        effective_at=first.snapshot.effective_at.astimezone(
            timezone(timedelta(hours=2))
        ).isoformat()
    )
    assert first.snapshot.effective_at == other.snapshot.effective_at
    assert first.snapshot.snapshot_id != other.snapshot.snapshot_id


def test_policy_hash_and_parameters_cannot_disagree():
    p = policy_evidence()
    with pytest.raises(PackageExecutionError):
        replace(
            p,
            parameters=tuple(
                (k, "changed" if k == "normalization" else v) for k, v in p.parameters
            ),
        )
    with pytest.raises(PackageExecutionError):
        replace(p, entity_type="vendor")
    with pytest.raises(PackageExecutionError):
        replace(p, parameters=list(p.parameters))
