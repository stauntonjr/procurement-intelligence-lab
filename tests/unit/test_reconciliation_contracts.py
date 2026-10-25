"""Current operation evidence must not impersonate its historical producers."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionStatus
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconcileInvocation,
    RetainedReconciliationRequest,
    same_reconciliation_computation,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    OperationAuthorityEvidence,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
)
from tests.bom_stage_fixtures import AT
from tests.reconciliation_fixtures import empty_receipt, operation_inputs, producer


def test_receipt_has_one_actual_stage_and_twelve_dispositions(tmp_path: Path):
    r = empty_receipt(tmp_path)
    assert len(r.entries) == 12
    assert r.entries[6].stage is StageId.RECONCILE
    assert r.entries[6].status is ExecutionStatus.SUCCEEDED
    assert all(e.status is ExecutionStatus.NOT_EXECUTED for i, e in enumerate(r.entries) if i != 6)
    assert r.requested_operation_complete and not r.package_execution_complete
    assert [
        e.status.value for e in r.output.inputs.recorded_producers[0].completed.execution.entries
    ] == ["SUCCEEDED"] * 6 + ["NOT_EXECUTED"] * 6
    assert RetainedReconciliationRequest(r.output.inputs, r.context).inputs is r.output.inputs
    invocation = ReconcileInvocation(
        r.output.provenance,
        r.output.inputs.scope,
        AT,
        (r.output.inputs.policy.reference,),
        r.output.inputs.input_ids,
    )
    assert invocation.stage is StageId.RECONCILE


def test_empty_operation_has_real_event(tmp_path: Path):
    r = empty_receipt(tmp_path)
    assert not r.output.decisions and not r.output.states
    assert r.output.batch_id in r.output.event.output_ids
    assert r.entries[6].event_id == r.output.event.event_id


def test_producer_order_and_raw_authority_format_preserve_computation(tmp_path: Path):
    r = empty_receipt(tmp_path)
    authority = replace(
        r.output.inputs.authority, raw_json=b" \n" + r.output.inputs.authority.raw_json
    )
    changed = replace(
        r,
        output=replace(r.output, inputs=replace(r.output.inputs, authority=authority)),
        completed_at=AT + timedelta(seconds=5),
    )
    assert same_reconciliation_computation(r, changed)
    assert r.execution_digest == changed.execution_digest
    assert r.receipt_digest != changed.receipt_digest


def test_full_producer_content_substitution_breaks_binding(tmp_path: Path):
    r = empty_receipt(tmp_path / "a")
    p, _ = producer(tmp_path / "b")
    with pytest.raises(PackageExecutionContractError):
        replace(r.output, inputs=operation_inputs((p,)))
    with pytest.raises(PackageExecutionError):
        replace(
            r.output.inputs,
            recorded_producers=(
                *r.output.inputs.recorded_producers,
                *r.output.inputs.recorded_producers,
            ),
        )


def test_invalid_output_membership_is_contract_failure(tmp_path: Path):
    r = empty_receipt(tmp_path)
    for changes in [
        {"entries": r.entries[:6]},
        {"completed_at": AT},
        {"context": replace(r.context, run_id="other")},
    ]:
        with pytest.raises(PackageExecutionContractError):
            replace(r, **changes)
    with pytest.raises(PackageExecutionContractError):
        replace(r.output, outside_predicate_ids=("foreign",))
    with pytest.raises(PackageExecutionError):
        OperationAuthorityEvidence("x", b"x" * 65537, b"{}")


@pytest.mark.parametrize("audit", [b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b'{ "x":1}', b"[]"])
def test_domain_audit_is_canonical_unambiguous_json(tmp_path: Path, audit: bytes):
    r = empty_receipt(tmp_path)
    with pytest.raises(PackageExecutionContractError):
        replace(r.output, domain_audit=audit)
