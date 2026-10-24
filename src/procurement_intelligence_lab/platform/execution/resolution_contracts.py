"""Additive six-stage request and receipt; five-stage contracts remain unchanged."""

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    ExecutionStatus,
    PrefixExecutionReceipt,
    ResolvedReference,
    StageExecutionEntry,
    plan_payload,
    validate_context,
    validate_references,
)
from procurement_intelligence_lab.platform.execution.identity import aware, canonical, digest, same
from procurement_intelligence_lab.platform.execution.outputs import immutable_output, require
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateInputEvidence,
    ResolutionPolicyEvidence,
    admit,
)
from procurement_intelligence_lab.platform.execution.resolution_outputs import ResolvedOutput
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)


@dataclass(frozen=True)
class ResolvedExecutionRequest:
    prefix: ExecutionRequest
    candidate_input: CandidateInputEvidence
    policy: ResolutionPolicyEvidence
    stop_after: StageId

    def __post_init__(self) -> None:
        admit(
            type(self.prefix) is ExecutionRequest
            and type(self.candidate_input) is CandidateInputEvidence
            and type(self.policy) is ResolutionPolicyEvidence
            and self.stop_after is StageId.RESOLVE
        )
        c = self.candidate_input.snapshot
        admit(
            same(c.scope, self.prefix.source.scope)
            and c.effective_at <= self.prefix.captured_at
            and c.entity_type == self.policy.entity_type
            and c.identifier_namespace == self.policy.identifier_namespace
        )


@dataclass(frozen=True)
class ResolveInvocation:
    provenance: DecisionProvenance
    captured_at: datetime
    references: tuple[ResolvedReference, ...]
    candidate_snapshot_id: str

    def __post_init__(self) -> None:
        admit(type(self.provenance) is DecisionProvenance)
        validate_context(self.provenance.context)
        aware(self.captured_at)
        validate_references(self.references)
        from procurement_intelligence_lab.platform.execution.identity import text

        text(self.candidate_snapshot_id)
        admit(
            self.provenance.component_kind is ComponentKind.DETERMINISTIC
            and all(
                getattr(self.provenance, key) is None
                for key in ("model_provider", "model_id", "model_revision", "prompt_version")
            )
        )

    @property
    def stage(self) -> StageId:
        return StageId.RESOLVE


@dataclass(frozen=True)
class ResolvedPrefixExecutionReceipt:
    prefix: PrefixExecutionReceipt
    candidate_input: CandidateInputEvidence
    policy: ResolutionPolicyEvidence
    output: ResolvedOutput
    entries: tuple[StageExecutionEntry, ...]
    completed_at: datetime

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.prefix) is PrefixExecutionReceipt
            and type(self.output) is ResolvedOutput
            and type(self.candidate_input) is CandidateInputEvidence
            and type(self.policy) is ResolutionPolicyEvidence
        )
        aware(self.completed_at)
        require(self.completed_at >= self.prefix.completed_at)
        require(
            same(self.output.previous, self.prefix.output)
            and same(self.output.candidates, self.candidate_input.snapshot)
            and same(self.output.policy, self.policy)
        )
        require(
            type(self.entries) is tuple
            and len(self.entries) == 12
            and all(type(e) is StageExecutionEntry for e in self.entries)
        )
        require(
            same(self.entries[:5], self.prefix.entries[:5])
            and same(self.entries[6:], self.prefix.entries[6:])
        )
        b = plan_payload(self.prefix.plan)["stages"][5]
        p, e = self.output.provenance, self.entries[5]
        require(
            b["mode"] == "EXECUTE"
            and b["domain_config_ref"] is None
            and b["policy_refs"] == [self.policy.reference.declaration_ref]
        )
        implementation = b["implementation"]
        require(
            e.stage is StageId.RESOLVE
            and e.mode.value == b["mode"]
            and e.status is ExecutionStatus.SUCCEEDED
            and e.implementation_id == p.component_name == implementation["implementation_id"]
            and p.implementation_version == implementation["implementation_version"]
            and p.component_kind is ComponentKind.DETERMINISTIC
        )
        require(
            all(
                getattr(p, k) is None
                for k in ("model_provider", "model_id", "model_revision", "prompt_version")
            )
        )
        expected_context = replace(
            self.prefix.context,
            input_snapshot_ids=tuple(
                dict.fromkeys((*self.prefix.context.input_snapshot_ids, *self.output.input_ids))
            ),
        )
        require(same(p.context, expected_context) and p.schema_version is None)
        require(
            e.input_ids == self.output.input_ids
            and e.output_ids == self.output.reference_ids
            and e.event_id == self.output.event.event_id
        )

    @property
    def plan(self):
        return self.prefix.plan

    @property
    def context(self):
        return self.prefix.context

    @property
    def requested_prefix_complete(self) -> bool:
        return True

    @property
    def package_execution_complete(self) -> bool:
        return False

    @property
    def computation_payload(self) -> bytes:
        return canonical(
            (
                "resolved-prefix-execution-v1",
                self.prefix.computation_payload,
                self.candidate_input.snapshot,
                self.policy,
                self.output,
                self.entries,
            )
        )

    @property
    def execution_digest(self) -> str:
        return sha256(self.computation_payload).hexdigest()

    @property
    def receipt_digest(self) -> str:
        return digest(self)
