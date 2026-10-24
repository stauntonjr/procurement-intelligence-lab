"""Mechanics for an explicitly injected sixth strategy and core audit callbacks."""

from collections.abc import Callable
from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.identity import same
from procurement_intelligence_lab.platform.execution.outputs import AssertedOutput, require
from procurement_intelligence_lab.platform.execution.resolution_contracts import ResolveInvocation
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateSnapshot,
    ResolutionPolicyEvidence,
)
from procurement_intelligence_lab.platform.execution.resolution_outputs import (
    MentionResolution,
    ResolvedOutput,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    EntityMention,
    ResolutionDecision,
)
from procurement_intelligence_lab.platform.semantics.strategies import ResolveStrategy


@dataclass(frozen=True)
class BomResolveExecutor:
    strategy: ResolveStrategy
    candidates: CandidateSnapshot
    policy: ResolutionPolicyEvidence
    audit_outcomes: Callable[
        [tuple[EntityMention, ...], tuple[ResolutionDecision, ...]], tuple[MentionResolution, ...]
    ]
    validate_output: Callable[[ResolvedOutput], None]

    def invoke(self, inputs: AssertedOutput, *, invocation: ResolveInvocation) -> ResolvedOutput:
        require(type(inputs) is AssertedOutput and type(invocation) is ResolveInvocation)
        require(
            invocation.candidate_snapshot_id == self.candidates.snapshot_id
            and same(invocation.references, (self.policy.reference,))
        )
        decisions, links = self.strategy.resolve(
            inputs.mentions, inputs.assertions, provenance=invocation.provenance
        )
        outcomes = self.audit_outcomes(inputs.mentions, decisions)
        linked = {c.assertion.assertion_id for c in links}
        result = ResolvedOutput(
            inputs,
            self.candidates,
            self.policy,
            outcomes,
            links,
            tuple(a.assertion_id for a in inputs.assertions if a.assertion_id not in linked),
            invocation.provenance,
        )
        self.validate_output(result)
        return result
