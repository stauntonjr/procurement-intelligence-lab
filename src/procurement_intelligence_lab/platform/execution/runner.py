"""Invoke an admitted fixed prefix over actual typed preceding outputs."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix
from procurement_intelligence_lab.platform.execution.contracts import (
    PREFIX,
    ExecutionStatus,
    PrefixExecutionReceipt,
    StageExecutionEntry,
    StageInvocation,
    plan_payload,
)
from procurement_intelligence_lab.platform.execution.identity import aware, same
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    CapturedOutput,
    MappedOutput,
    NormalizedOutput,
    StageInput,
    StageOutput,
    StructuredOutput,
    require,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import AssertionOrigin
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)


@dataclass(frozen=True)
class PrefixExecution:
    output: AssertedOutput
    receipt: PrefixExecutionReceipt

    def __post_init__(self) -> None:
        require(type(self.receipt) is PrefixExecutionReceipt and self.receipt.output is self.output)


def run_prefix(prepared: PreparedPrefix, *, clock: Callable[[], datetime]) -> PrefixExecution:
    if type(prepared) is not PreparedPrefix:
        raise PackageExecutionError("execution requires an admitted prefix")
    before = clock()
    aware(before)
    if before < prepared.request.captured_at:
        raise PackageExecutionError("execution cannot start in the future")
    inputs: StageInput = prepared.request.source
    actuals: list[StageOutput] = []
    for stage, registration in zip(PREFIX, prepared.selected, strict=True):
        direct = (
            (inputs.reference_id,)
            if isinstance(inputs, SourceReference)
            else inputs.reference_ids[:1]
        )
        if stage is StageId.NORMALIZE:
            assert registration.policy_version is not None
            direct += (registration.policy_version,)
        if type(inputs) is NormalizedOutput:
            origin = AssertionOrigin(
                inputs.previous.previous.previous.artifact,
                inputs.batch_id,
                inputs.event,
                prepared.request.captured_at,
            )
            direct = (inputs.batch_id, inputs.event.event_id, origin.origin_id)
        context = replace(
            prepared.context,
            input_snapshot_ids=tuple(
                dict.fromkeys((*prepared.context.input_snapshot_ids, *direct))
            ),
        )
        p = DecisionProvenance(
            context,
            registration.descriptor.implementation_id,
            ComponentKind.DETERMINISTIC,
            registration.descriptor.implementation_version,
            policy_version=registration.policy_version,
            schema_version=registration.schema_version,
        )
        invocation = StageInvocation(
            stage, p, prepared.request.captured_at, registration.references
        )
        result = registration.executor.invoke(inputs, invocation=invocation)
        expected = (
            CapturedOutput,
            StructuredOutput,
            MappedOutput,
            NormalizedOutput,
            AssertedOutput,
        )[len(actuals)]
        require(type(result) is expected)
        require(same(result.event.provenance, p) and same(result.source, prepared.request.source))
        if isinstance(result, CapturedOutput):
            require(same(result.artifact.captured_at, prepared.request.captured_at))
        else:
            require(result.previous is inputs)
        if type(result) is MappedOutput:
            binding = plan_payload(prepared.plan)["stages"][2]
            schema = next(
                r
                for r in registration.references
                if r.declaration_ref == binding["domain_config_ref"]
            )
            require(result.document.mapping_schema == schema.reference_id)
        if type(result) is NormalizedOutput:
            require(result.policy_reference == registration.policy_version)
        if type(result) is AssertedOutput:
            require(same(result.origin.recorded_at, prepared.request.captured_at))
        actuals.append(result)
        if not isinstance(result, AssertedOutput):
            inputs = result
    output = actuals[-1]
    assert type(output) is AssertedOutput
    after = clock()
    aware(after)
    if after < before:
        raise PackageExecutionError("completion clock cannot precede execution")
    entries: list[StageExecutionEntry] = []
    for i, binding in enumerate(plan_payload(prepared.plan)["stages"]):
        a = actuals[i] if i < 5 else None
        entries.append(
            StageExecutionEntry(
                StageId(binding["stage"]),
                StageMode(binding["mode"]),
                ExecutionStatus.SUCCEEDED if a else ExecutionStatus.NOT_EXECUTED,
                None if a else "outside_requested_prefix",
                a.event.provenance.component_name if a else None,
                a.input_ids if a else (),
                a.reference_ids if a else (),
                a.event.event_id if a else None,
            )
        )
    receipt = PrefixExecutionReceipt(
        prepared.plan,
        prepared.context,
        prepared.request.source,
        prepared.references,
        output,
        tuple(entries),
        after,
    )
    return PrefixExecution(output, receipt)
