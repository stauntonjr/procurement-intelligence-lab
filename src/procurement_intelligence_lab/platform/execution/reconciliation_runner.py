"""Invoke exactly one actual current executor; historical producers stay historical."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionStatus,
    StageExecutionEntry,
    plan_payload,
)
from procurement_intelligence_lab.platform.execution.identity import aware, same
from procurement_intelligence_lab.platform.execution.outputs import require
from procurement_intelligence_lab.platform.execution.reconciliation_admission import (
    PreparedReconciliation,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconcileInvocation,
    ReconciliationOperationReceipt,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)


def run_reconciliation(
    prepared: PreparedReconciliation, *, clock: Callable[[], datetime]
) -> ReconciliationOperationReceipt:
    admit(type(prepared) is PreparedReconciliation)
    before = clock()
    aware(before)
    admit(before >= prepared.request.context.started_at)
    inputs = prepared.request.inputs
    reg = prepared.registration
    context = replace(
        prepared.request.context,
        input_snapshot_ids=tuple(
            dict.fromkeys((*prepared.request.context.input_snapshot_ids, *inputs.input_ids))
        ),
    )
    provenance = DecisionProvenance(
        context,
        reg.descriptor.implementation_id,
        ComponentKind.DETERMINISTIC,
        reg.descriptor.implementation_version,
        policy_version=reg.policy_version,
    )
    invocation = ReconcileInvocation(
        provenance, inputs.scope, inputs.as_of, reg.references, inputs.input_ids
    )
    output = reg.executor.invoke(inputs, invocation=invocation)
    require(
        type(output) is ReconciledOutput
        and same(output.inputs, inputs)
        and same(output.provenance, provenance)
    )
    after = clock()
    aware(after)
    admit(after >= before)
    bindings = plan_payload(prepared.plan)["stages"]
    entries = tuple(
        StageExecutionEntry(
            stage,
            StageMode(bindings[i]["mode"]),
            ExecutionStatus.SUCCEEDED
            if stage is StageId.RECONCILE
            else ExecutionStatus.NOT_EXECUTED,
            None if stage is StageId.RECONCILE else "outside_requested_prefix",
            provenance.component_name if stage is StageId.RECONCILE else None,
            inputs.input_ids if stage is StageId.RECONCILE else (),
            output.reference_ids if stage is StageId.RECONCILE else (),
            output.event.event_id if stage is StageId.RECONCILE else None,
        )
        for i, stage in enumerate(StageId)
    )
    return ReconciliationOperationReceipt(
        prepared.plan, prepared.request.context, output, entries, after
    )
