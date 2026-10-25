"""Admit only the current RECONCILE registration over retained producer evidence."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import (
    ResolvedReference,
    plan_payload,
    validate_references,
)
from procurement_intelligence_lab.platform.execution.identity import aware, same, text
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconcileInvocation,
    RetainedReconciliationRequest,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationDescriptor,
    ImplementationRegistry,
    PhysicalPlan,
    StageSelection,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest


class ReconcileExecutor(Protocol):
    def invoke(
        self, inputs: RetainedReconciliationInputs, *, invocation: ReconcileInvocation
    ) -> ReconciledOutput: ...


@dataclass(frozen=True)
class ReconcileExecutorRegistration:
    descriptor: ImplementationDescriptor
    settings: tuple[tuple[str, str], ...]
    references: tuple[ResolvedReference, ...]
    executor: ReconcileExecutor
    policy_version: str

    def __post_init__(self) -> None:
        admit(
            type(self.descriptor) is ImplementationDescriptor
            and self.descriptor.stage is StageId.RECONCILE
        )
        StageSelection(
            StageId.RECONCILE,
            self.descriptor.implementation_id,
            self.descriptor.config_schema_version,
            self.settings,
        )
        validate_references(self.references)
        text(self.policy_version)
        admit(len(self.references) == 1 and self.policy_version == self.references[0].reference_id)
        admit(
            self.descriptor.provider_version is None
            and self.descriptor.model_version is None
            and callable(getattr(self.executor, "invoke", None))
        )


@dataclass(frozen=True)
class PreparedReconciliation:
    plan: PhysicalPlan
    request: RetainedReconciliationRequest
    registration: ReconcileExecutorRegistration

    def __post_init__(self) -> None:
        admit(
            type(self.request) is RetainedReconciliationRequest
            and type(self.registration) is ReconcileExecutorRegistration
        )
        payload = plan_payload(self.plan)
        b = payload["stages"][6]
        reg = self.registration
        admit(payload["application_version"] == self.request.context.code_revision)
        metadata = asdict(reg.descriptor)
        for name in ("capabilities", "required_settings", "optional_settings"):
            metadata[name] = sorted(metadata[name])
        admit(
            b["mode"] == "EXECUTE"
            and b["domain_config_ref"] is None
            and b["policy_refs"] == [self.request.inputs.policy.reference.declaration_ref]
        )
        admit(
            same(b["implementation"], metadata)
            and reg.references == (self.request.inputs.policy.reference,)
        )


def prepare_reconciliation(
    manifest: bytes,
    *,
    registry: ImplementationRegistry,
    config: ImplementationConfig,
    request: RetainedReconciliationRequest,
    registration: ReconcileExecutorRegistration,
    now: datetime,
) -> PreparedReconciliation:
    aware(now)
    admit(now >= request.context.started_at)
    plan = plan_manifest(manifest, registry=registry, config=config)
    selection = next((s for s in config.selections if s.stage is StageId.RECONCILE), None)
    admit(selection is not None)
    assert selection is not None
    descriptor = next(
        (d for d in registry.implementations if d.implementation_id == selection.implementation_id),
        None,
    )
    admit(
        same(descriptor, registration.descriptor)
        and tuple(sorted(selection.settings)) == tuple(sorted(registration.settings))
    )
    return PreparedReconciliation(plan, request, registration)
