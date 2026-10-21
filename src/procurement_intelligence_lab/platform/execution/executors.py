"""Explicit runtime implementations; never loaded from declarative data."""

from dataclasses import dataclass
from typing import Protocol

from procurement_intelligence_lab.platform.execution.contracts import (
    ResolvedReference,
    StageInvocation,
    validate_references,
)
from procurement_intelligence_lab.platform.execution.identity import text
from procurement_intelligence_lab.platform.execution.outputs import StageInput, StageOutput
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationDescriptor,
    StageSelection,
)
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError


class StageExecutor(Protocol):
    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> StageOutput: ...


@dataclass(frozen=True)
class ExecutorRegistration:
    descriptor: ImplementationDescriptor
    settings: tuple[tuple[str, str], ...]
    references: tuple[ResolvedReference, ...]
    executor: StageExecutor
    policy_version: str | None = None
    schema_version: str | None = None

    def __post_init__(self) -> None:
        if type(self.descriptor) is not ImplementationDescriptor or not callable(
            getattr(self.executor, "invoke", None)
        ):
            raise PackageExecutionError("runtime requires an explicit descriptor and executor")
        StageSelection(
            self.descriptor.stage,
            self.descriptor.implementation_id,
            self.descriptor.config_schema_version,
            self.settings,
        )
        validate_references(self.references)
        for v in (self.policy_version, self.schema_version):
            if v is not None:
                text(v)


@dataclass(frozen=True)
class ExecutorRegistry:
    registrations: tuple[ExecutorRegistration, ...]

    def __post_init__(self) -> None:
        if type(self.registrations) is not tuple or any(
            type(x) is not ExecutorRegistration for x in self.registrations
        ):
            raise PackageExecutionError("runtime requires immutable executor registrations")
        ids = tuple(x.descriptor.implementation_id for x in self.registrations)
        if len(ids) != len(set(ids)):
            raise PackageExecutionError("runtime executor IDs must be unique")
