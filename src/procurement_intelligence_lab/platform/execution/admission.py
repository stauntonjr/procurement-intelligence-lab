"""Admission checks complete before source/content access or any executor call."""

from dataclasses import dataclass, replace
from datetime import datetime

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import (
    PREFIX,
    ExecutionRequest,
    ResolvedReference,
    plan_payload,
)
from procurement_intelligence_lab.platform.execution.executors import (
    ExecutorRegistration,
    ExecutorRegistry,
)
from procurement_intelligence_lab.platform.execution.identity import aware, digest, same
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationRegistry,
    PhysicalPlan,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext


def reject(condition: bool) -> None:
    if not condition:
        raise PackageExecutionError(
            "selected prefix executor, descriptor, settings or resolved policy is incompatible"
        )


@dataclass(frozen=True)
class PreparedPrefix:
    manifest: bytes
    registry: ImplementationRegistry
    config: ImplementationConfig
    executors: ExecutorRegistry
    request: ExecutionRequest
    plan: PhysicalPlan

    def __post_init__(self) -> None:
        reject(type(self.request) is ExecutionRequest and type(self.executors) is ExecutorRegistry)
        expected = plan_manifest(self.manifest, registry=self.registry, config=self.config)
        reject(same(expected, self.plan))
        reject(self.request.context.code_revision == self.config.application_version)
        payload = plan_payload(self.plan)
        all_refs: dict[str, ResolvedReference] = {}
        by_id = {r.descriptor.implementation_id: r for r in self.executors.registrations}
        advertised = {d.implementation_id: d for d in self.registry.implementations}
        selections = {s.stage: s for s in self.config.selections}
        for stage, binding in zip(PREFIX, payload["stages"][:5], strict=True):
            reject(binding["mode"] == "EXECUTE")
            selection = selections[stage]
            reg = by_id.get(selection.implementation_id)
            reject(reg is not None)
            assert reg is not None
            reject(same(reg.descriptor, advertised[selection.implementation_id]))
            reject(
                reg.descriptor.stage is stage
                and reg.descriptor.provider_version is None
                and reg.descriptor.model_version is None
            )
            reject(tuple(sorted(reg.settings)) == tuple(sorted(selection.settings)))
            keys = tuple(
                sorted(
                    (
                        *binding["policy_refs"],
                        *((binding["domain_config_ref"],) if binding["domain_config_ref"] else ()),
                    )
                )
            )
            reject(tuple(r.declaration_ref for r in reg.references) == keys)
            if stage in (StageId.NORMALIZE, StageId.ASSERT):
                reject(len(binding["policy_refs"]) == 1)
                policy = next(
                    r for r in reg.references if r.declaration_ref == binding["policy_refs"][0]
                )
                reject(reg.policy_version == policy.reference_id)
            else:
                reject(reg.policy_version is None)
            if stage is StageId.MAP:
                reject(binding["domain_config_ref"] is not None and reg.schema_version is not None)
            elif stage is not StageId.STRUCTURE:
                reject(reg.schema_version is None)
            for r in reg.references:
                reject(r.declaration_ref not in all_refs or same(r, all_refs[r.declaration_ref]))
                all_refs[r.declaration_ref] = r

    @property
    def selected(self) -> tuple[ExecutorRegistration, ...]:
        selections = {s.stage: s.implementation_id for s in self.config.selections}
        registered = {r.descriptor.implementation_id: r for r in self.executors.registrations}
        return tuple(registered[selections[s]] for s in PREFIX)

    @property
    def references(self) -> tuple[ResolvedReference, ...]:
        refs = {r.declaration_ref: r for e in self.selected for r in e.references}
        return tuple(refs[k] for k in sorted(refs))

    @property
    def context(self) -> ProvenanceContext:
        metadata = tuple((r.references, r.policy_version, r.schema_version) for r in self.selected)
        return replace(
            self.request.context, config_digest=digest((self.request.context, self.plan, metadata))
        )


def prepare_prefix(
    manifest: bytes,
    *,
    registry: ImplementationRegistry,
    config: ImplementationConfig,
    executors: ExecutorRegistry,
    request: ExecutionRequest,
    now: datetime,
) -> PreparedPrefix:
    aware(now)
    reject(type(request) is ExecutionRequest)
    reject(request.captured_at <= now)
    plan = plan_manifest(manifest, registry=registry, config=config)
    return PreparedPrefix(manifest, registry, config, executors, request, plan)
