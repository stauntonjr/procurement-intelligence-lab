"""Run the admitted first-five prefix once, then its actual sixth executor."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionStatus,
    StageExecutionEntry,
)
from procurement_intelligence_lab.platform.execution.identity import aware, same
from procurement_intelligence_lab.platform.execution.outputs import require
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
)
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedPrefixExecutionReceipt,
    ResolveInvocation,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.execution.resolution_outputs import (
    ResolvedOutput,
    resolution_input_ids,
)
from procurement_intelligence_lab.platform.execution.runner import run_prefix
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)


@dataclass(frozen=True)
class ResolvedPrefixExecution:
    output: ResolvedOutput
    receipt: ResolvedPrefixExecutionReceipt

    def __post_init__(self) -> None:
        require(
            type(self.receipt) is ResolvedPrefixExecutionReceipt
            and self.receipt.output is self.output
        )


def run_resolved_prefix(
    prepared: PreparedResolvedPrefix, *, clock: Callable[[], datetime]
) -> ResolvedPrefixExecution:
    admit(type(prepared) is PreparedResolvedPrefix)
    before = clock()
    aware(before)
    admit(before >= prepared.request.prefix.captured_at)
    prefix = run_prefix(prepared.prefix, clock=clock)
    reg = prepared.registration
    inputs = resolution_input_ids(
        prefix.output, prepared.request.candidate_input.snapshot, prepared.request.policy
    )
    context = replace(
        prefix.receipt.context,
        input_snapshot_ids=tuple(
            dict.fromkeys((*prefix.receipt.context.input_snapshot_ids, *inputs))
        ),
    )
    provenance = DecisionProvenance(
        context,
        reg.descriptor.implementation_id,
        ComponentKind.DETERMINISTIC,
        reg.descriptor.implementation_version,
        policy_version=reg.policy_version,
    )
    invocation = ResolveInvocation(
        provenance,
        prepared.request.prefix.captured_at,
        reg.references,
        prepared.request.candidate_input.snapshot.snapshot_id,
    )
    result = reg.executor.invoke(prefix.output, invocation=invocation)
    require(
        type(result) is ResolvedOutput
        and result.previous is prefix.output
        and same(result.candidates, prepared.request.candidate_input.snapshot)
        and same(result.policy, prepared.request.policy)
        and same(result.provenance, provenance)
    )
    after = clock()
    aware(after)
    admit(after >= prefix.receipt.completed_at and after >= before)
    entries = list(prefix.receipt.entries)
    entries[5] = StageExecutionEntry(
        StageId.RESOLVE,
        StageMode.EXECUTE,
        ExecutionStatus.SUCCEEDED,
        None,
        reg.descriptor.implementation_id,
        result.input_ids,
        result.reference_ids,
        result.event.event_id,
    )
    receipt = ResolvedPrefixExecutionReceipt(
        prefix.receipt,
        prepared.request.candidate_input,
        prepared.request.policy,
        result,
        tuple(entries),
        after,
    )
    return ResolvedPrefixExecution(result, receipt)
