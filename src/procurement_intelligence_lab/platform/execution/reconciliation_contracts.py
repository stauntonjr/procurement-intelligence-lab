"""Separate recorded-producer request and current one-stage execution receipt."""

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionStatus,
    ResolvedReference,
    StageExecutionEntry,
    plan_payload,
    validate_context,
    validate_references,
)
from procurement_intelligence_lab.platform.execution.identity import aware, canonical, digest, same
from procurement_intelligence_lab.platform.execution.outputs import immutable_output, require
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.planning.contracts import PhysicalPlan
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class RetainedReconciliationRequest:
    inputs: RetainedReconciliationInputs
    context: ProvenanceContext

    def __post_init__(self) -> None:
        admit(type(self.inputs) is RetainedReconciliationInputs)
        validate_context(self.context)
        admit(self.inputs.as_of <= self.context.started_at)
        admit(
            all(
                p.completed.prefix.snapshot.artifact.captured_at <= self.context.started_at
                for p in self.inputs.recorded_producers
            )
        )


@dataclass(frozen=True)
class ReconcileInvocation:
    provenance: DecisionProvenance
    scope: StateScope
    as_of: datetime
    references: tuple[ResolvedReference, ...]
    input_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        admit(type(self.provenance) is DecisionProvenance and type(self.scope) is StateScope)
        validate_context(self.provenance.context)
        validate_references(self.references)
        aware(self.as_of)
        admit(
            self.as_of <= self.provenance.context.started_at
            and type(self.input_ids) is tuple
            and bool(self.input_ids)
        )
        admit(
            self.provenance.component_kind is ComponentKind.DETERMINISTIC
            and all(
                getattr(self.provenance, k) is None
                for k in ("model_provider", "model_id", "model_revision", "prompt_version")
            )
        )

    @property
    def stage(self) -> StageId:
        return StageId.RECONCILE


@dataclass(frozen=True)
class ReconciliationOperationReceipt:
    plan: PhysicalPlan
    context: ProvenanceContext
    output: ReconciledOutput
    entries: tuple[StageExecutionEntry, ...]
    completed_at: datetime

    def __post_init__(self) -> None:
        immutable_output(self)
        require(type(self.output) is ReconciledOutput and type(self.context) is ProvenanceContext)
        validate_context(self.context)
        aware(self.completed_at)
        require(
            self.completed_at >= self.context.started_at
            and self.output.inputs.as_of <= self.context.started_at
        )
        require(
            all(
                p.completed.prefix.snapshot.artifact.captured_at <= self.context.started_at
                for p in self.output.inputs.recorded_producers
            )
        )
        stages = plan_payload(self.plan)["stages"]
        require(
            type(self.entries) is tuple
            and len(self.entries) == 12
            and all(type(e) is StageExecutionEntry for e in self.entries)
        )
        for b, e, stage in zip(stages, self.entries, StageId, strict=True):
            require(e.stage is stage and e.mode.value == b["mode"])
            if stage is StageId.RECONCILE:
                p = self.output.provenance
                require(
                    b["mode"] == "EXECUTE"
                    and b["domain_config_ref"] is None
                    and b["policy_refs"] == [self.output.inputs.policy.reference.declaration_ref]
                )
                require(
                    e.status is ExecutionStatus.SUCCEEDED
                    and e.implementation_id
                    == p.component_name
                    == b["implementation"]["implementation_id"]
                    and p.implementation_version == b["implementation"]["implementation_version"]
                )
                require(
                    e.input_ids == self.output.inputs.input_ids
                    and e.output_ids == self.output.reference_ids
                    and e.event_id == self.output.event.event_id
                )
            else:
                require(e.status is ExecutionStatus.NOT_EXECUTED)
        expected = replace(
            self.context,
            input_snapshot_ids=tuple(
                dict.fromkeys((*self.context.input_snapshot_ids, *self.output.inputs.input_ids))
            ),
        )
        require(same(self.output.provenance.context, expected))
        require(plan_payload(self.plan)["application_version"] == self.context.code_revision)

    @property
    def requested_operation_complete(self) -> bool:
        return True

    @property
    def package_execution_complete(self) -> bool:
        return False

    @property
    def computation_payload(self) -> bytes:
        return canonical(
            (
                "retained-resolution-reconciliation-v1",
                self.plan,
                self.context,
                self.output.inputs.semantic_payload,
                self.output.semantic_output,
                self.entries,
            )
        )

    @property
    def execution_digest(self) -> str:
        return sha256(self.computation_payload).hexdigest()

    @property
    def receipt_digest(self) -> str:
        return digest(self)


def same_reconciliation_computation(
    left: ReconciliationOperationReceipt, right: ReconciliationOperationReceipt
) -> bool:
    return left.computation_payload == right.computation_payload
