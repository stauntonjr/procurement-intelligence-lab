from dataclasses import replace
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab.bootstrap import (
    build_bom_assertion_service,
    compile_procurement_manifest,
)
from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA
from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    ExecutionStatus,
    PrefixExecutionReceipt,
    ResolvedReference,
    StageExecutionEntry,
)
from procurement_intelligence_lab.platform.execution.identity import digest
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
    refs = tuple(
        sorted(
            (
                ResolvedReference(
                    BOM_TABLE_SCHEMA.reference_id,
                    BOM_TABLE_SCHEMA.reference_id,
                    digest(BOM_TABLE_SCHEMA),
                ),
                ResolvedReference(
                    "procurement.normalize/bom-decimal@1", POLICY.reference_id, digest(POLICY)
                ),
                ResolvedReference(
                    "procurement.assert/bom-claims@1",
                    "bom-assertions@1",
                    digest(("bom-assertions@1", "1")),
                ),
            ),
            key=lambda r: r.declaration_ref,
        )
    )
    return PrefixExecutionReceipt(
        plan, provenance().context, a.source, refs, a, entries, AT + timedelta(seconds=1)
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


def test_request_rejects_untyped_scope_without_raw_python_failure(tmp_path: Path):
    a = output(tmp_path)
    with pytest.raises(SemanticContractError):
        ExecutionRequest(
            replace(a.source, scope=cast(Any, "scope")), provenance().context, AT, StageId.ASSERT
        )


@pytest.mark.parametrize(
    "mode",
    [
        "missing-revision",
        "missing-mode",
        "missing-implementation",
        "wrong-schema",
        "capability-int",
    ],
)
def test_retained_plan_shape_fails_typed_even_with_matching_hash(tmp_path: Path, mode: str):
    import json
    from hashlib import sha256

    from procurement_intelligence_lab.platform.execution.identity import canonical

    r = receipt(tmp_path)
    data = json.loads(r.plan.canonical_json)
    if mode == "missing-revision":
        del data["application_version"]
    elif mode == "missing-mode":
        del data["stages"][0]["mode"]
    elif mode == "missing-implementation":
        data["stages"][0]["implementation"] = None
    elif mode == "capability-int":
        data["stages"][1]["capability_checks"][0]["satisfied"] = 1
    else:
        data["plan_schema_version"] = "999"
    content = canonical(data)
    with pytest.raises(SemanticContractError):
        replace(
            r, plan=replace(r.plan, canonical_json=content, plan_hash=sha256(content).hexdigest())
        )


@pytest.mark.parametrize(
    "mode", ["elements", "fields", "cells", "mention-claims", "context-snapshots", "event-edges"]
)
def test_output_rejects_mutable_nested_collections(tmp_path: Path, mode: str):
    a = output(tmp_path)
    m = a.previous.previous
    s = m.previous
    c = s.previous
    with pytest.raises(SemanticContractError):
        if mode == "elements":
            replace(s, document=replace(s.document, elements=cast(Any, list(s.document.elements))))
        elif mode == "fields":
            replace(m, document=replace(m.document, fields=cast(Any, list(m.document.fields))))
        elif mode == "cells":
            element = s.document.elements[0]
            location = element.evidence.location
            evidence = replace(
                element.evidence,
                location=replace(cast(Any, location), cells=list(element.evidence.cells)),
            )
            element = replace(element, evidence=evidence)
            replace(s, document=replace(s.document, elements=(element, *s.document.elements[1:])))
        elif mode == "mention-claims":
            mention = replace(a.mentions[0], assertions=cast(Any, list(a.mentions[0].assertions)))
            replace(a, mentions=(mention, *a.mentions[1:]))
        elif mode == "context-snapshots":
            p = c.artifact.provenance
            p = replace(
                p,
                context=replace(
                    p.context, input_snapshot_ids=cast(Any, list(p.context.input_snapshot_ids))
                ),
            )
            replace(c, artifact=replace(c.artifact, provenance=p))
        else:
            replace(c, event=replace(c.event, input_edges=cast(Any, list(c.event.input_edges))))


@pytest.mark.parametrize(
    "changes",
    [
        {"input_snapshot_ids": ["source"]},
        {"input_snapshot_ids": ("source", "source")},
        {"environment": [("mode", "local")]},
        {"environment": (("mode",),)},
        {"environment": (["mode", "local"],)},
        {"environment": (("mode", "local"), ("mode", "other"))},
        {"environment": (("mode", ""),)},
        {"parent_run_id": ""},
        {"dependency_lock_digest": ""},
    ],
    ids=[
        "mutable-snapshots",
        "duplicate-snapshots",
        "mutable-environment",
        "short-pair",
        "mutable-pair",
        "duplicate-keys",
        "empty-value",
        "empty-parent",
        "empty-lock",
    ],
)
def test_request_rejects_ambiguous_or_mutable_context_metadata(
    tmp_path: Path, changes: dict[str, Any]
):
    from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError

    a = output(tmp_path)
    context = replace(provenance().context, **changes)
    with pytest.raises(PackageExecutionError):
        ExecutionRequest(a.source, context, AT, StageId.ASSERT)


def test_request_keeps_explicit_immutable_environment_and_parent_identity(tmp_path: Path):
    a = output(tmp_path)
    context = replace(
        provenance().context,
        environment=(("mode", "local"), ("region", "synthetic")),
        parent_run_id="parent",
        dependency_lock_digest="lock",
    )
    request = ExecutionRequest(a.source, context, AT, StageId.ASSERT)
    assert request.context is context
    assert digest(request) != digest(
        replace(request, context=replace(context, parent_run_id="other-parent"))
    )
