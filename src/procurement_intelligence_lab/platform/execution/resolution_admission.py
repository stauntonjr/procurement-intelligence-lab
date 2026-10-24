"""Explicit sixth registration admission without weakening the five-stage boundary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix, prepare_prefix
from procurement_intelligence_lab.platform.execution.contracts import (
    ResolvedReference,
    plan_payload,
    validate_references,
)
from procurement_intelligence_lab.platform.execution.executors import ExecutorRegistry
from procurement_intelligence_lab.platform.execution.identity import same, text
from procurement_intelligence_lab.platform.execution.outputs import AssertedOutput
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
    ResolveInvocation,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.execution.resolution_outputs import ResolvedOutput
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationDescriptor,
    ImplementationRegistry,
    StageSelection,
)


class ResolveExecutor(Protocol):
    def invoke(
        self, inputs: AssertedOutput, *, invocation: ResolveInvocation
    ) -> ResolvedOutput: ...


@dataclass(frozen=True)
class ResolveExecutorRegistration:
    descriptor: ImplementationDescriptor
    settings: tuple[tuple[str, str], ...]
    references: tuple[ResolvedReference, ...]
    executor: ResolveExecutor
    policy_version: str

    def __post_init__(self) -> None:
        admit(
            type(self.descriptor) is ImplementationDescriptor
            and self.descriptor.stage is StageId.RESOLVE
        )
        admit(callable(getattr(self.executor, "invoke", None)))
        StageSelection(
            StageId.RESOLVE,
            self.descriptor.implementation_id,
            self.descriptor.config_schema_version,
            self.settings,
        )
        validate_references(self.references)
        text(self.policy_version)


@dataclass(frozen=True)
class PreparedResolvedPrefix:
    prefix: PreparedPrefix
    request: ResolvedExecutionRequest
    registration: ResolveExecutorRegistration

    def __post_init__(self) -> None:
        admit(
            type(self.prefix) is PreparedPrefix
            and type(self.request) is ResolvedExecutionRequest
            and type(self.registration) is ResolveExecutorRegistration
        )
        admit(same(self.prefix.request, self.request.prefix))
        reg = self.registration
        binding = plan_payload(self.prefix.plan)["stages"][5]
        admit(
            binding["mode"] == "EXECUTE"
            and binding["domain_config_ref"] is None
            and binding["policy_refs"] == [self.request.policy.reference.declaration_ref]
        )
        selection = next(
            (s for s in self.prefix.config.selections if s.stage is StageId.RESOLVE), None
        )
        admit(selection is not None)
        assert selection is not None
        advertised = next(
            (
                d
                for d in self.prefix.registry.implementations
                if d.implementation_id == selection.implementation_id
            ),
            None,
        )
        admit(
            same(advertised, reg.descriptor)
            and reg.descriptor.provider_version is None
            and reg.descriptor.model_version is None
        )
        admit(tuple(sorted(reg.settings)) == tuple(sorted(selection.settings)))
        admit(
            reg.references == (self.request.policy.reference,)
            and reg.policy_version == self.request.policy.reference.reference_id
        )


def prepare_resolved_prefix(
    manifest: bytes,
    *,
    registry: ImplementationRegistry,
    config: ImplementationConfig,
    executors: ExecutorRegistry,
    resolution: ResolveExecutorRegistration,
    request: ResolvedExecutionRequest,
    now: datetime,
) -> PreparedResolvedPrefix:
    admit(type(request) is ResolvedExecutionRequest)
    prefix = prepare_prefix(
        manifest,
        registry=registry,
        config=config,
        executors=executors,
        request=request.prefix,
        now=now,
    )
    return PreparedResolvedPrefix(prefix, request, resolution)
