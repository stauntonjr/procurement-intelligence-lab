from dataclasses import replace
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab.bootstrap import (
    build_bom_assertion_service,
    compile_procurement_manifest,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    ExecutionStatus,
    PrefixExecutionReceipt,
    ResolvedReference,
    StageExecutionEntry,
)
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    CapturedOutput,
    MappedOutput,
    NormalizedOutput,
    StructuredOutput,
)
from procurement_intelligence_lab.platform.planning.inputs import load_config, load_registry
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source


def output(tmp_path: Path, rows: str = HEADER + ROW):
    r = build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(source(workbook(tmp_path / "source.xlsx", rows)))
    d = r.normalized.stages
    c = CapturedOutput(d.artifact, d.transformations[0])
    s = StructuredOutput(c, d.structured, d.transformations[1])
    m = MappedOutput(s, d.mapped, d.transformations[2])
    n = NormalizedOutput(
        m, r.normalized.observations, r.normalized.provenance, r.normalized.policy_reference
    )
    a = AssertedOutput(n, r.assertions, r.mentions, r.origin, r.provenance)
    assert n.event == r.normalized.transformation and a.event == r.transformation
    return a


def receipt(tmp_path: Path):
    a = output(tmp_path)
    registry = load_registry(Path("tests/fixtures/planning/procurement-registry.json").read_bytes())
    config = load_config(Path("tests/fixtures/planning/procurement-config.toml").read_bytes())
    chain = a.chain
    descriptors = list(registry.implementations)
    selections = list(config.selections)
    for i, item in enumerate(chain):
        p = item.event.provenance
        descriptors[i] = replace(
            descriptors[i],
            implementation_id=p.component_name,
            implementation_version=p.implementation_version,
        )
        selections[i] = replace(selections[i], implementation_id=p.component_name)
    registry = replace(registry, implementations=tuple(descriptors))
    config = replace(
        config, application_version=provenance().context.code_revision, selections=tuple(selections)
    )
    plan = plan_manifest(
        compile_procurement_manifest().canonical_json, registry=registry, config=config
    )
    entries = tuple(
        StageExecutionEntry(
            stage,
            StageMode.EXECUTE if i < 9 else StageMode.EMPTY,
            ExecutionStatus.SUCCEEDED if i < 5 else ExecutionStatus.NOT_EXECUTED,
            None if i < 5 else "outside_requested_prefix",
            chain[i].event.provenance.component_name if i < 5 else None,
            chain[i].input_ids if i < 5 else (),
            chain[i].reference_ids if i < 5 else (),
            chain[i].event.event_id if i < 5 else None,
        )
        for i, stage in enumerate(StageId)
    )
    return PrefixExecutionReceipt(
        plan, provenance().context, a.source, (), a, entries, AT + timedelta(seconds=1)
    )


def test_actual_chain_retains_batch_identity_and_explicit_partial_completion(tmp_path: Path):
    r = receipt(tmp_path)
    assert r.requested_prefix_complete is True and r.package_execution_complete is False
    assert tuple(x.stage for x in r.entries) == tuple(StageId)
    assert all(x.event_id is None and not x.output_ids for x in r.entries[5:])
    assert len(r.output.assertions) == 4
    assert r.output.reference_ids[0] == r.output.batch_id


@pytest.mark.parametrize(
    "rows",
    [
        HEADER,
        HEADER + ROW + ROW.replace("7", "8"),
        HEADER + '<row r="7"><c r="C7"><v>0</v></c></row>',
    ],
)
def test_empty_duplicate_and_unknown_batches_keep_real_evidence(tmp_path: Path, rows: str):
    a = output(tmp_path, rows)
    assert a.event.output_ids[0] == a.batch_id
    assert len(a.assertions) == len(a.previous.observations)
    assert len({x.assertion_id for x in a.assertions}) == len(a.assertions)
    if rows == HEADER:
        assert a.assertions == a.mentions == ()
    elif "A7" in rows:
        assert len(a.mentions) == 2 and a.mentions[0].text == a.mentions[1].text
    else:
        assert any(x.value is None for x in a.assertions)


@pytest.mark.parametrize("stage", range(3))
def test_output_cannot_replace_real_event_edges(tmp_path: Path, stage: int):
    a = output(tmp_path)
    item = a.chain[stage]
    with pytest.raises(SemanticContractError):
        replace(item, event=replace(item.event, output_ids=("invented",)))


@pytest.mark.parametrize("mode", ["status", "event", "order", "source", "context", "plan"])
def test_receipt_rejects_contradictory_or_substituted_evidence(tmp_path: Path, mode: str):
    r = receipt(tmp_path)
    with pytest.raises(SemanticContractError):
        if mode in ["status", "event"]:
            e = r.entries[-1]
            e = (
                replace(e, status=ExecutionStatus.SUCCEEDED)
                if mode == "status"
                else replace(e, event_id="invented")
            )
            replace(r, entries=(*r.entries[:-1], e))
        elif mode == "order":
            replace(r, entries=tuple(reversed(r.entries)))
        elif mode == "source":
            replace(r, source=replace(r.source, source_version="other"))
        elif mode == "context":
            replace(r, context=replace(r.context, code_revision="other"))
        else:
            replace(r, plan=replace(r.plan, plan_hash="0" * 64))


def test_receipt_identity_binds_encoding_and_separates_attempt_time(tmp_path: Path):
    r = receipt(tmp_path)
    later = replace(r, completed_at=r.completed_at + timedelta(seconds=1))
    assert r.execution_digest == later.execution_digest and r.receipt_digest != later.receipt_digest
    offset = replace(r, completed_at=r.completed_at.astimezone(timezone(timedelta(hours=2))))
    assert r.completed_at == offset.completed_at and r.receipt_digest != offset.receipt_digest


@pytest.mark.parametrize("mode", ["stage", "unicode", "naive", "order", "context_type"])
def test_request_preflight_is_intrinsic(tmp_path: Path, mode: str):
    a = output(tmp_path)
    ctx = provenance().context
    with pytest.raises(SemanticContractError):
        ExecutionRequest(
            a.source,
            cast(Any, "context")
            if mode == "context_type"
            else replace(ctx, run_id="bad\ud800")
            if mode == "unicode"
            else ctx,
            AT.replace(tzinfo=None)
            if mode == "naive"
            else AT - timedelta(seconds=1)
            if mode == "order"
            else AT,
            StageId.DETECT if mode == "stage" else StageId.ASSERT,
        )


@pytest.mark.parametrize("digest", ["x", "f" * 63, "F" * 64, cast(Any, None)])
def test_resolved_reference_requires_portable_full_digest(digest: Any):
    with pytest.raises(SemanticContractError):
        ResolvedReference("declaration", "instance", digest)


def test_payload_containers_and_origin_cannot_be_substituted(tmp_path: Path):
    a = output(tmp_path)
    with pytest.raises(SemanticContractError):
        replace(a, assertions=cast(Any, list(a.assertions)))
    with pytest.raises(SemanticContractError):
        replace(a, assertions=(*a.assertions, a.assertions[0]))
    with pytest.raises(SemanticContractError):
        replace(a, origin=replace(a.origin, recorded_at=AT + timedelta(seconds=1)))
    with pytest.raises(SemanticContractError):
        replace(a.previous, observations=tuple(reversed(a.previous.observations)))
