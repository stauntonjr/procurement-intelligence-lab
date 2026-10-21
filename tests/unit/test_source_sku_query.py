from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab.domains.procurement.source_queries import (
    SourceSkuQuery,
    query_provenance,
    validate_execution,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import SourceQueryContractError
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance
from tests.contract.test_postgres_archive import inputs


def execution(snapshot_id: str):
    return replace(
        provenance().context,
        workflow_name="archived-source-sku-query",
        workflow_version="1",
        input_snapshot_ids=(snapshot_id,),
        started_at=AT + timedelta(seconds=1),
    )


def test_real_query_deduplicates_values_but_retains_each_source_root(tmp_path: Path):
    snapshot, _ = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8"))
    result = SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))
    assert result.value == ("GPU-A",)
    assert result.status is EpistemicStatus.OBSERVED
    assert len(result.inputs) == 2
    assert len({a.assertion_id for a in result.inputs}) == 2
    assert result.known_skus == ("GPU-A",) and result.missing_assertion_ids == ()
    assert tuple(e.target_id for e in result.event.input_edges) == tuple(
        sorted(a.assertion_id for a in result.inputs)
    )
    assert result.event.output_ids == (result.reference_id,)
    assert result.event.provenance == result.provenance
    assert [a.evidence.cells for a in result.inputs] == [("A",), ("A",)]


def test_missing_source_sku_never_reports_complete_subset(tmp_path: Path):
    missing = ROW.replace('<c r="A7"><v>GPU-A</v></c>', "")
    snapshot, _ = inputs(tmp_path, HEADER + missing)
    result = SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))
    assert result.value is None and result.status is EpistemicStatus.UNRESOLVED
    assert result.known_skus == ()
    assert result.missing_assertion_ids == tuple(a.assertion_id for a in result.inputs)
    assert len(result.event.input_edges) == 1


def test_empty_source_does_not_invent_a_registered_answer(tmp_path: Path):
    snapshot, _ = inputs(tmp_path, HEADER)
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))


def test_reference_binds_complete_execution_and_source(tmp_path: Path):
    snapshot, _ = inputs(tmp_path)
    ctx = execution(snapshot.snapshot_id)
    first = SourceSkuQuery(snapshot, query_provenance(ctx))
    changed = SourceSkuQuery(snapshot, query_provenance(replace(ctx, parent_run_id="parent")))
    assert first.value == changed.value
    assert first.execution_digest != changed.execution_digest
    assert first.reference_id != changed.reference_id
    assert SourceSkuQuery(snapshot, query_provenance(ctx)) == first
    assert len(first.execution_digest) == 64


@pytest.mark.parametrize(
    "changes",
    [
        {"input_snapshot_ids": ("foreign",)},
        {"input_snapshot_ids": ()},
        {"started_at": AT - timedelta(seconds=1)},
        {"environment": (("private", "unsupported"),)},
        {"code_revision": "bad\ud800text"},
        {"run_id": " "},
        {"image_digest": "x" * 501},
    ],
)
def test_invalid_execution_is_intrinsically_rejected(tmp_path: Path, changes: dict[str, Any]):
    snapshot, _ = inputs(tmp_path)
    ctx = replace(execution(snapshot.snapshot_id), **changes)
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(snapshot, query_provenance(ctx))


def test_wrong_component_and_runtime_types_are_rejected(tmp_path: Path):
    snapshot, _ = inputs(tmp_path)
    p = query_provenance(execution(snapshot.snapshot_id))
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(snapshot, replace(p, component_name="arbitrary"))
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(snapshot, cast(Any, "untyped"))
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(cast(Any, "untyped"), p)
    with pytest.raises(SourceQueryContractError):
        validate_execution(cast(Any, "untyped"), snapshot.snapshot_id)


def test_partial_unknown_retains_known_tokens_without_completeness(tmp_path: Path):
    second = ROW.replace("7", "8").replace('<c r="A8"><v>GPU-A</v></c>', "")
    snapshot, _ = inputs(tmp_path, HEADER + ROW + second)
    result = SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))
    assert result.value is None and result.known_skus == ("GPU-A",)
    assert len(result.inputs) == 2 and len(result.missing_assertion_ids) == 1


def test_source_aliases_are_not_implicitly_canonicalized(tmp_path: Path):
    snapshot, _ = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8").replace("GPU-A", "gpu-a"))
    result = SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))
    assert result.value == ("GPU-A", "gpu-a")


@pytest.mark.parametrize("count", [32, 33])
def test_registration_root_limit_is_explicit(tmp_path: Path, count: int):
    snapshot, _ = inputs(
        tmp_path, HEADER + "".join(ROW.replace("7", str(i)) for i in range(2, count + 2))
    )
    if count == 33:
        with pytest.raises(SourceQueryContractError):
            SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id)))
    else:
        assert (
            len(SourceSkuQuery(snapshot, query_provenance(execution(snapshot.snapshot_id))).inputs)
            == 32
        )


def test_wrong_typed_predicate_cannot_silently_drop_a_source_row(tmp_path: Path):
    from enum import StrEnum

    class Foreign(StrEnum):
        HAS_SKU = "has_sku"

    snapshot, _ = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8").replace("GPU-A", "GPU-B"))
    first = next(a for a in snapshot.assertions if a.predicate.value == "has_sku")
    claims = tuple(
        replace(a, predicate=Foreign.HAS_SKU) if a is first else a for a in snapshot.assertions
    )
    altered = replace(snapshot, assertions=claims)
    with pytest.raises(SourceQueryContractError):
        SourceSkuQuery(altered, query_provenance(execution(altered.snapshot_id)))
