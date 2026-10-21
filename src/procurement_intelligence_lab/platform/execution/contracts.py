"""Validated request, invocation and positively evidenced partial-run receipts."""

import json
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any, cast

from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.identity import (
    aware,
    canonical,
    digest,
    digest_text,
    same,
    text,
)
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    StageOutput,
    require,
)
from procurement_intelligence_lab.platform.planning.contracts import PhysicalPlan
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)

PREFIX = tuple(StageId)[:5]


def validate_context(context: ProvenanceContext) -> None:
    if type(context) is not ProvenanceContext:
        raise PackageExecutionError("execution requires a typed context")
    for value in (
        context.run_id,
        context.workflow_name,
        context.workflow_version,
        context.code_revision,
        context.image_digest,
        context.config_digest,
    ):
        text(value)
    for value in (context.dependency_lock_digest, context.parent_run_id):
        if value is not None:
            text(value)
    if type(context.input_snapshot_ids) is not tuple or type(context.environment) is not tuple:
        raise PackageExecutionError("execution context requires immutable metadata")
    for value in context.input_snapshot_ids:
        text(value)
    if len(set(context.input_snapshot_ids)) != len(context.input_snapshot_ids):
        raise PackageExecutionError("execution snapshots must be unique")
    for pair in context.environment:
        if type(pair) is not tuple or len(pair) != 2:
            raise PackageExecutionError("execution environment requires immutable text pairs")
        for value in pair:
            text(value)
    if len({p[0] for p in context.environment}) != len(context.environment):
        raise PackageExecutionError("execution environment keys must be unique")
    aware(context.started_at)
    canonical(context)


@dataclass(frozen=True)
class ExecutionRequest:
    source: SourceReference
    context: ProvenanceContext
    captured_at: datetime
    stop_after: StageId

    def __post_init__(self) -> None:
        if (
            type(self.source) is not SourceReference
            or type(self.stop_after) is not StageId
            or self.stop_after is not StageId.ASSERT
        ):
            raise PackageExecutionError("execution supports one source through ASSERT only")
        validate_context(self.context)
        aware(self.captured_at)
        aware(self.source.observed_at)
        for value in (
            self.source.source_system,
            self.source.source_uri,
            *vars(self.source.scope).values(),
        ):
            text(value)
        if self.source.source_version is not None:
            text(self.source.source_version)
        if self.source.observed_at > self.captured_at or not same(
            self.captured_at, self.context.started_at
        ):
            raise PackageExecutionError(
                "source observation must precede explicit capture/execution start"
            )
        canonical(self)


@dataclass(frozen=True)
class ResolvedReference:
    declaration_ref: str
    reference_id: str
    content_digest: str

    def __post_init__(self) -> None:
        text(self.declaration_ref)
        text(self.reference_id)
        digest_text(self.content_digest)


def validate_references(references: tuple[ResolvedReference, ...]) -> None:
    if type(references) is not tuple or any(type(r) is not ResolvedReference for r in references):
        raise PackageExecutionError("execution references require immutable resolved records")
    keys = tuple(r.declaration_ref for r in references)
    if keys != tuple(sorted(set(keys))):
        raise PackageExecutionError("resolved declarations must be unique and canonically ordered")


@dataclass(frozen=True)
class StageInvocation:
    stage: StageId
    provenance: DecisionProvenance
    captured_at: datetime
    references: tuple[ResolvedReference, ...]

    def __post_init__(self) -> None:
        if (
            type(self.stage) is not StageId
            or self.stage not in PREFIX
            or type(self.provenance) is not DecisionProvenance
        ):
            raise PackageExecutionError("unsupported typed stage invocation")
        validate_context(self.provenance.context)
        aware(self.captured_at)
        validate_references(self.references)
        if self.provenance.component_kind is not ComponentKind.DETERMINISTIC or any(
            getattr(self.provenance, k) is not None
            for k in ("model_provider", "model_id", "model_revision", "prompt_version")
        ):
            raise PackageExecutionError("prefix invocation must retain deterministic metadata")
        text(self.provenance.component_name)
        text(self.provenance.implementation_version)
        canonical(self)


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NOT_EXECUTED = "NOT_EXECUTED"


@dataclass(frozen=True)
class StageExecutionEntry:
    stage: StageId
    mode: StageMode
    status: ExecutionStatus
    reason: str | None
    implementation_id: str | None
    input_ids: tuple[str, ...]
    output_ids: tuple[str, ...]
    event_id: str | None

    def __post_init__(self) -> None:
        require(
            type(self.stage) is StageId
            and type(self.mode) is StageMode
            and type(self.status) is ExecutionStatus
        )
        require(type(self.input_ids) is tuple and type(self.output_ids) is tuple)
        for value in (*self.input_ids, *self.output_ids):
            text(value)
        if self.status is ExecutionStatus.NOT_EXECUTED:
            require(
                self.reason == "outside_requested_prefix"
                and self.implementation_id is None
                and self.event_id is None
                and not self.input_ids
                and not self.output_ids
            )
        else:
            require(
                self.mode is StageMode.EXECUTE
                and self.reason is None
                and bool(self.input_ids)
                and bool(self.output_ids)
            )
            text(self.implementation_id)
            text(self.event_id)


def plan_payload(plan: PhysicalPlan) -> dict[str, Any]:
    if type(plan) is not PhysicalPlan or type(plan.canonical_json) is not bytes:
        raise PackageExecutionError("receipt requires a typed canonical plan")
    if sha256(plan.canonical_json).hexdigest() != plan.plan_hash:
        raise PackageExecutionError("plan digest does not match retained bytes")
    try:
        raw: object = json.loads(plan.canonical_json)
        if not isinstance(raw, dict):
            raise TypeError
        data = cast(dict[str, Any], raw)
        if canonical(data) != plan.canonical_json:
            raise ValueError
        if len(data["stages"]) != 12 or tuple(x["stage"] for x in data["stages"]) != tuple(
            s.value for s in StageId
        ):
            raise ValueError
    except (ValueError, KeyError, TypeError, RecursionError):
        raise PackageExecutionError("invalid retained plan payload") from None
    return cast(dict[str, Any], data)


def input_snapshots(output: StageOutput) -> tuple[str, ...]:
    if type(output) is AssertedOutput:
        return (output.previous.batch_id, output.previous.event.event_id, output.origin.origin_id)
    return output.input_ids


@dataclass(frozen=True)
class PrefixExecutionReceipt:
    plan: PhysicalPlan
    context: ProvenanceContext
    source: SourceReference
    references: tuple[ResolvedReference, ...]
    output: AssertedOutput
    entries: tuple[StageExecutionEntry, ...]
    completed_at: datetime

    def __post_init__(self) -> None:
        validate_context(self.context)
        aware(self.completed_at)
        validate_references(self.references)
        require(
            type(self.output) is AssertedOutput
            and type(self.source) is SourceReference
            and same(self.output.source, self.source)
        )
        require(
            type(self.entries) is tuple
            and all(type(x) is StageExecutionEntry for x in self.entries)
        )
        require(tuple(x.stage for x in self.entries) == tuple(StageId))
        require(self.completed_at >= self.context.started_at)
        payload = plan_payload(self.plan)
        require(payload["application_version"] == self.context.code_revision)
        for i, (entry, binding) in enumerate(zip(self.entries, payload["stages"], strict=True)):
            require(entry.mode.value == binding["mode"])
            if i >= 5:
                require(entry.status is ExecutionStatus.NOT_EXECUTED)
                continue
            actual = self.output.chain[i]
            p = actual.event.provenance
            expected_context = replace(
                self.context,
                input_snapshot_ids=tuple(
                    dict.fromkeys((*self.context.input_snapshot_ids, *input_snapshots(actual)))
                ),
            )
            require(same(p.context, expected_context))
            require(
                entry.status is ExecutionStatus.SUCCEEDED
                and entry.implementation_id
                == binding["implementation"]["implementation_id"]
                == p.component_name
                and p.implementation_version == binding["implementation"]["implementation_version"]
            )
            require(
                entry.input_ids == actual.input_ids
                and entry.output_ids == actual.reference_ids
                and entry.event_id == actual.event.event_id
            )

    @property
    def requested_prefix_complete(self) -> bool:
        return True

    @property
    def package_execution_complete(self) -> bool:
        return False

    @property
    def execution_digest(self) -> str:
        return digest(
            (self.plan, self.context, self.source, self.references, self.output, self.entries)
        )

    @property
    def receipt_digest(self) -> str:
        return digest(self)
