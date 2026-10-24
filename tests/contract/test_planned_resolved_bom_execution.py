"""Actual six-stage composition, exact source continuity and legacy compatibility."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.domains.procurement.planned_resolution import BomResolve
from procurement_intelligence_lab.platform.execution.resolution_runner import run_resolved_prefix
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    SemanticContractError,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.contract.test_bom_assertions import POLICY
from tests.resolved_execution_fixtures import catalog, planned_resolved_inputs
from tests.unit.test_planned_bom_resolution import supported_policy

pytestmark = pytest.mark.contract


def service(inputs: Any):
    manifest, registry, config, q, _ = inputs
    return bootstrap.build_planned_resolved_bom_service(
        manifest=manifest,
        registry=registry,
        config=config,
        normalization_policy=POLICY,
        resolution_policy=supported_policy(),
        candidate_input=q.candidate_input,
        clock=lambda: AT + timedelta(seconds=1),
    )


def test_six_real_stages_run_once_from_actual_previous_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.adapters.package_document_executors import (
        AssertExecutor,
        CaptureExecutor,
        MapExecutor,
        NormalizeExecutor,
        StructureExecutor,
    )

    calls: list[str] = []

    def wrap(cls: Any, name: str):
        original = cls.invoke

        def invoke(self: Any, inputs: Any, *, invocation: Any):
            calls.append(name)
            return original(self, inputs, invocation=invocation)

        monkeypatch.setattr(cls, "invoke", invoke)

    for cls, name in [
        (CaptureExecutor, "INGEST"),
        (StructureExecutor, "STRUCTURE"),
        (MapExecutor, "MAP"),
        (NormalizeExecutor, "NORMALIZE"),
        (AssertExecutor, "ASSERT"),
    ]:
        wrap(cls, name)
    original = BomResolve.resolve

    def resolve(self: BomResolve, mentions: Any, assertions: Any, *, provenance: Any):
        calls.append("RESOLVE")
        return original(self, mentions, assertions, provenance=provenance)

    monkeypatch.setattr(BomResolve, "resolve", resolve)
    inputs = planned_resolved_inputs(tmp_path)
    result = service(inputs).execute(inputs[3])
    assert calls == ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT", "RESOLVE"]
    assert result.execution.output.previous is result.execution.receipt.prefix.output
    data = result.as_dict()
    assert data["executed_stages"] == calls
    assert len(data["transformations"]) == 6
    assert data["resolution"]["outcomes"][0]["canonical_key"] == "GPU-A"
    assert data["execution_receipt"]["stop_after"] == "RESOLVE"
    assert data["prefix_execution_receipt"]["stop_after"] == "ASSERT"
    assert not data["execution_receipt"]["package_execution_complete"]


@pytest.mark.parametrize("rows", [HEADER, HEADER + ROW])
def test_all_twelve_entries_and_real_empty_sixth_event(tmp_path: Path, rows: str):
    inputs = planned_resolved_inputs(tmp_path, rows=rows)
    r = service(inputs).execute(inputs[3]).execution.receipt
    assert len(r.entries) == 12
    assert [e.status.value for e in r.entries] == ["SUCCEEDED"] * 6 + ["NOT_EXECUTED"] * 6
    assert r.entries[5].event_id == r.output.event.event_id
    assert r.output.event.parent_event_ids == (r.prefix.output.event.event_id,)
    assert all(not e.event_id for e in r.entries[6:])


def test_standalone_first_five_compute_same_on_equal_pins(tmp_path: Path):
    inputs = planned_resolved_inputs(tmp_path)
    m, r, c, q, _ = inputs
    six = service(inputs).execute(q).execution.receipt
    five = (
        bootstrap.build_planned_bom_service(
            manifest=m, registry=r, config=c, policy=POLICY, clock=lambda: AT + timedelta(seconds=1)
        )
        .execute(q.prefix)
        .execution.receipt
    )
    assert six.prefix.execution_digest == five.execution_digest
    assert six.prefix.receipt_digest == five.receipt_digest


def test_resolve_failure_publishes_no_sixth_success(tmp_path: Path):
    from procurement_intelligence_lab.platform.execution.outputs import AssertedOutput
    from procurement_intelligence_lab.platform.execution.resolution_contracts import (
        ResolveInvocation,
    )
    from procurement_intelligence_lab.platform.execution.resolution_outputs import ResolvedOutput

    class Broken:
        def invoke(
            self, inputs: AssertedOutput, *, invocation: ResolveInvocation
        ) -> ResolvedOutput:
            raise PackageExecutionContractError("test failure")

    inputs = planned_resolved_inputs(tmp_path)
    s = service(inputs)
    bad = replace(s, resolution=replace(s.resolution, executor=Broken()))
    with pytest.raises(PackageExecutionContractError):
        bad.execute(inputs[3])


def test_completion_clock_must_not_regress(tmp_path: Path):
    inputs = planned_resolved_inputs(tmp_path)
    prepared = service(inputs).prepare(inputs[3])
    times = iter([AT + timedelta(seconds=s) for s in (1, 1, 2, 1)])
    with pytest.raises(SemanticContractError):
        run_resolved_prefix(prepared, clock=lambda: next(times))


def test_pinned_catalog_cannot_change_after_service_composition(tmp_path: Path):
    inputs = planned_resolved_inputs(tmp_path, source_exists=False)
    with pytest.raises(SemanticContractError):
        service(inputs).execute(replace(inputs[3], candidate_input=catalog(("CPU-A",))))


def test_catalog_order_format_and_content_identity(tmp_path: Path):
    import json

    from procurement_intelligence_lab.platform.execution.resolution_inputs import (
        load_candidate_input,
    )
    from tests.resolved_execution_fixtures import catalog_wire

    inputs = planned_resolved_inputs(tmp_path, keys=("GPU-A", "CPU-A"))
    s = service(inputs)
    first = s.execute(inputs[3]).execution.receipt
    reformatted = load_candidate_input(
        json.dumps(catalog_wire(("CPU-A", "GPU-A")), indent=2).encode()
    )
    current = s.execute(replace(inputs[3], candidate_input=reformatted)).execution.receipt
    assert current.execution_digest == first.execution_digest
    assert current.receipt_digest != first.receipt_digest
    changed_catalog = catalog(("CPU-A",))
    new_request = replace(inputs[3], candidate_input=changed_catalog)
    changed_inputs = (*inputs[:3], new_request, inputs[4])
    changed = service(changed_inputs).execute(new_request).execution.receipt
    assert changed.prefix.execution_digest == first.prefix.execution_digest
    assert changed.execution_digest != first.execution_digest
    assert changed.output.outcomes[0].decision.canonical_key is None
