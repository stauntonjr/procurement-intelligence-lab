"""One actual current stage, with exact plan and immutable invocation evidence."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab.bootstrap import (
    bom_reconciliation_descriptor,
    compile_procurement_manifest,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.reconciliation_admission import (
    ReconcileExecutorRegistration,
    prepare_reconciliation,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    RetainedReconciliationRequest,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.reconciliation_runner import run_reconciliation
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationRegistry,
    StageSelection,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
)
from tests.bom_stage_fixtures import AT, HEADER, provenance
from tests.planning_fixtures import planning_inputs
from tests.reconciliation_fixtures import operation_inputs, producer


class EmptyExecutor:
    calls = 0

    def invoke(self, inputs: Any, *, invocation: Any):
        self.calls += 1
        outside = tuple(
            sorted(
                a.assertion_id
                for p in inputs.recorded_producers
                for a in p.completed.execution.output.previous.assertions
            )
        )
        return ReconciledOutput(inputs, (), (), outside, b"{}", invocation.provenance)


def runtime():
    m = compile_procurement_manifest(
        source_profile="retained-resolved-required-quantity"
    ).canonical_json
    r, c = planning_inputs(m)
    d = bom_reconciliation_descriptor()
    r = ImplementationRegistry(
        "1.0", tuple(d if x.stage is StageId.RECONCILE else x for x in r.implementations)
    )
    c = replace(
        c,
        selections=tuple(
            StageSelection(StageId.RECONCILE, d.implementation_id, d.config_schema_version)
            if x.stage is StageId.RECONCILE
            else x
            for x in c.selections
        ),
    )
    return m, r, c


def prepared(tmp_path: Path):
    p, _ = producer(tmp_path, HEADER)
    inputs = operation_inputs((p,))
    m, r, c = runtime()
    context = replace(
        provenance().context, started_at=AT + timedelta(seconds=3), code_revision="test-build"
    )
    executor = EmptyExecutor()
    registration = ReconcileExecutorRegistration(
        bom_reconciliation_descriptor(),
        (),
        (inputs.policy.reference,),
        executor,
        inputs.policy.reference.reference_id,
    )
    q = RetainedReconciliationRequest(inputs, context)
    return prepare_reconciliation(
        m, registry=r, config=c, request=q, registration=registration, now=context.started_at
    ), executor


def test_each_retry_invokes_once(tmp_path: Path):
    p, e = prepared(tmp_path)
    a = run_reconciliation(p, clock=lambda: AT + timedelta(seconds=4))
    b = run_reconciliation(p, clock=lambda: AT + timedelta(seconds=5))
    assert (
        e.calls == 2
        and a.execution_digest == b.execution_digest
        and a.receipt_digest != b.receipt_digest
    )
    assert [x.status.value for x in a.entries].count("SUCCEEDED") == 1


def test_upstream_executor_factories_never_called(tmp_path: Path):
    p, e = prepared(tmp_path)
    assert run_reconciliation(
        p, clock=lambda: AT + timedelta(seconds=4)
    ).requested_operation_complete
    assert e.calls == 1  # No upstream registry/factory exists in the runner API.
    with pytest.raises(PackageExecutionError):
        run_reconciliation(p, clock=lambda: AT)


def test_invoked_metadata_substitution_fails_contract(tmp_path: Path):
    p, _ = prepared(tmp_path)
    with pytest.raises(PackageExecutionError):
        replace(p.registration, policy_version="foreign-policy")
    with pytest.raises(PackageExecutionContractError):
        replace(run_reconciliation(p, clock=lambda: AT + timedelta(seconds=4)), entries=())


def test_neutral_nonprocurement_operation(tmp_path: Path):
    import json

    from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
    from procurement_intelligence_lab.platform.execution.identity import digest
    from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
        OperationAuthorityEvidence,
        ReconciliationPolicyEvidence,
    )

    p, _e = prepared(tmp_path)
    raw = json.loads(p.plan.canonical_json)
    # Recompile an explicit foreign-domain manifest, retaining the same standardized contracts.
    m, r, c = runtime()
    manifest = json.loads(m)
    manifest["domain"]["id"] = "inventory"
    manifest["stages"][6]["policy_refs"] = ["inventory.reconcile/stock@1"]
    m = json.dumps(manifest).encode()
    plan = plan_manifest(m, registry=r, config=c)
    policy = ReconciliationPolicyEvidence(
        ResolvedReference("inventory.reconcile/stock@1", "inventory-stock/v1", digest({})), ()
    )
    inputs = replace(
        p.request.inputs,
        authority=OperationAuthorityEvidence("inventory-authority/v1", b"{}", b"{}"),
        policy=policy,
    )
    reg = replace(
        p.registration, references=(policy.reference,), policy_version=policy.reference.reference_id
    )
    other = replace(p, plan=plan, request=replace(p.request, inputs=inputs), registration=reg)
    assert (
        run_reconciliation(
            other, clock=lambda: AT + timedelta(seconds=4)
        ).output.provenance.policy_version
        == "inventory-stock/v1"
    )
    assert raw["domain"]["id"] == "procurement"


def test_original_bom_manifest_remains_byte_identical():
    assert (
        compile_procurement_manifest().manifest_hash
        == "8df445c4e5034ae0d7476872b9dcfecd91a2f4f6967acb66ea198523dada6970"
    )
