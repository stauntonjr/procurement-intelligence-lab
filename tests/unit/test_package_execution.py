from dataclasses import replace
from datetime import timedelta, timezone
from typing import Any, cast

import pytest

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.admission import prepare_prefix
from procurement_intelligence_lab.platform.execution.contracts import ExecutionStatus
from procurement_intelligence_lab.platform.execution.executors import ExecutorRegistry
from procurement_intelligence_lab.platform.execution.runner import run_prefix
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
)
from tests.bom_stage_fixtures import AT
from tests.execution_fixtures import EmptyExecutor, ExecutionInputs, executable_inputs


def prepare(data: ExecutionInputs | None = None):
    m, r, c, e, q, calls = data or executable_inputs()
    return prepare_prefix(m, registry=r, config=c, executors=e, request=q, now=AT), calls


def test_non_procurement_same_runner_and_unvisited_empty_is_not_success():
    p, calls = prepare()
    result = run_prefix(p, clock=lambda: AT + timedelta(seconds=1))
    assert calls == list(StageId)[:5]
    assert result.output.assertions == result.output.mentions == ()
    assert result.receipt.package_execution_complete is False
    assert [e.status for e in result.receipt.entries[5:]] == [ExecutionStatus.NOT_EXECUTED] * 7
    assert b"procurement" not in result.receipt.plan.canonical_json


def test_preflight_missing_executor_before_io():
    m, r, c, e, q, calls = executable_inputs()
    with pytest.raises(PackageExecutionError):
        prepare_prefix(
            m,
            registry=r,
            config=c,
            executors=replace(e, registrations=e.registrations[:-1]),
            request=q,
            now=AT,
        )
    assert calls == []


@pytest.mark.parametrize(
    "mode", ["descriptor", "settings", "reference", "clock", "revision", "policy", "model"]
)
def test_exact_descriptor_settings_and_references(mode: str):
    m, r, c, e, q, calls = executable_inputs()
    first = e.registrations[0]
    if mode == "descriptor":
        first = replace(first, descriptor=replace(first.descriptor, implementation_version="other"))
    elif mode == "settings":
        first = replace(first, settings=())
    elif mode == "reference":
        first = replace(first, references=e.registrations[2].references)
    elif mode == "revision":
        q = replace(q, context=replace(q.context, code_revision="other"))
    elif mode == "policy":
        first = replace(first, policy_version="unbound-policy")
    elif mode == "model":
        first = replace(first, descriptor=replace(first.descriptor, model_version="model"))
    e = replace(e, registrations=(first, *e.registrations[1:]))
    with pytest.raises(PackageExecutionError):
        prepare_prefix(
            m,
            registry=r,
            config=c,
            executors=e,
            request=q,
            now=AT - timedelta(seconds=1) if mode == "clock" else AT,
        )
    assert calls == []


def test_substituted_output_stops_chain():
    m, r, c, e, q, calls = executable_inputs()
    reg = e.registrations[1]
    e = replace(
        e,
        registrations=(
            e.registrations[0],
            replace(reg, executor=EmptyExecutor(StageId.STRUCTURE, calls, True)),
            *e.registrations[2:],
        ),
    )
    p, _ = prepare((m, r, c, e, q, calls))
    with pytest.raises(PackageExecutionContractError):
        run_prefix(p, clock=lambda: AT)
    assert calls == [StageId.INGEST, StageId.STRUCTURE]


def test_registry_order_invariance_and_full_encoded_identity():
    data = executable_inputs()
    m, r, c, e, q, calls = data
    first, _ = prepare(data)
    first = run_prefix(first, clock=lambda: AT)
    reordered, _ = prepare(
        (
            m,
            replace(r, implementations=tuple(reversed(r.implementations))),
            replace(c, selections=tuple(reversed(c.selections))),
            replace(e, registrations=tuple(reversed(e.registrations))),
            q,
            calls,
        )
    )
    second = run_prefix(reordered, clock=lambda: AT)
    assert first.receipt.execution_digest == second.receipt.execution_digest
    shifted = q.context.started_at.astimezone(timezone(timedelta(hours=2)))
    q = replace(q, captured_at=shifted, context=replace(q.context, started_at=shifted))
    changed, _ = prepare((m, r, c, e, q, calls))
    third = run_prefix(changed, clock=lambda: AT)
    assert third.receipt.execution_digest != first.receipt.execution_digest


def test_prepared_cannot_swap_plan_or_context_without_readmission():
    p, _ = prepare()
    with pytest.raises(PackageExecutionError):
        replace(p, plan=replace(p.plan, plan_hash="0" * 64))
    with pytest.raises(PackageExecutionError):
        replace(
            p, request=replace(p.request, context=replace(p.request.context, code_revision="wrong"))
        )


def test_duplicate_or_wrong_registry_shape_fails_intrinsically():
    e = executable_inputs()[3]
    with pytest.raises(PackageExecutionError):
        ExecutorRegistry((*e.registrations, e.registrations[0]))
    with pytest.raises(PackageExecutionError):
        ExecutorRegistry(cast(Any, list(e.registrations)))


def test_invalid_clock_stops_before_first_executor():
    p, calls = prepare()
    with pytest.raises(PackageExecutionError):
        run_prefix(p, clock=lambda: AT.replace(tzinfo=None))
    assert calls == []


def test_outside_executors_not_required_and_plan_metadata_remains_bound():
    import json

    from tests.planning_fixtures import planning_inputs

    m, _, _, e, q, calls = executable_inputs()
    payload = json.loads(m)
    for binding in payload["stages"][5:9]:
        binding.update(mode="EXECUTE", neutral_semantics=None)
    m = json.dumps(payload).encode()
    r, c = planning_inputs(m)
    c = replace(c, application_version=q.context.code_revision)
    p, _ = prepare((m, r, c, e, q, calls))
    result = run_prefix(p, clock=lambda: AT)
    assert len(p.selected) == 5 and len(c.selections) == 9
    assert all(x.status is ExecutionStatus.NOT_EXECUTED for x in result.receipt.entries[5:])
    payload["domain"]["version"] = "1.0.1"
    changed, _ = prepare((json.dumps(payload).encode(), r, c, e, q, calls))
    assert (
        run_prefix(changed, clock=lambda: AT).receipt.execution_digest
        != result.receipt.execution_digest
    )


@pytest.mark.parametrize("mode", ["EMPTY", "PASSTHROUGH"])
def test_rejects_neutral_prefix_before_invocation(mode: str):
    import json

    from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG
    from tests.planning_fixtures import planning_inputs

    m, _, _, e, q, calls = executable_inputs()
    payload = json.loads(m)
    binding = payload["stages"][1]
    binding.update(
        mode=mode,
        neutral_semantics=STAGE_CATALOG[1].empty_result if mode == "EMPTY" else None,
        output_contract_verified=mode == "PASSTHROUGH",
    )
    m = json.dumps(payload).encode()
    r, c = planning_inputs(m)
    c = replace(c, application_version=q.context.code_revision)
    with pytest.raises(PackageExecutionError):
        prepare_prefix(m, registry=r, config=c, executors=e, request=q, now=AT)
    assert calls == []
