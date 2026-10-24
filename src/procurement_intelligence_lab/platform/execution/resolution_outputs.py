"""Exact mention-bound resolution outputs, independent of a concrete matching algorithm."""

from dataclasses import dataclass

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.identity import digest, same, text
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    event,
    immutable_output,
    require,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateSnapshot,
    ResolutionPolicyEvidence,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    EntityMention,
    ResolutionDecision,
    ResolutionStatus,
)


def resolution_input_ids(
    previous: AssertedOutput, candidates: CandidateSnapshot, policy: ResolutionPolicyEvidence
) -> tuple[str, ...]:
    return (
        previous.batch_id,
        previous.event.event_id,
        *(m.mention_id for m in previous.mentions),
        *(a.assertion_id for a in previous.assertions),
        candidates.snapshot_id,
        policy.reference.reference_id,
    )


@dataclass(frozen=True)
class MentionResolution:
    mention: EntityMention
    decision: ResolutionDecision
    candidate_snapshot_id: str
    matched_keys: tuple[str, ...]
    policy_reference: str

    def __post_init__(self) -> None:
        immutable_output(self)
        require(type(self.mention) is EntityMention and type(self.decision) is ResolutionDecision)
        text(self.candidate_snapshot_id)
        text(self.policy_reference)
        require(type(self.matched_keys) is tuple and all(type(k) is str for k in self.matched_keys))
        require(self.matched_keys == tuple(sorted(set(self.matched_keys))))
        d, m = self.decision, self.mention
        require(d.mention == m.text and type(d.status) is ResolutionStatus)
        require(type(d.evidence) is tuple and bool(d.evidence))
        require(len({a.assertion_id for a in d.evidence}) == len(d.evidence))
        claims = {a.assertion_id: a for a in m.assertions}
        require(all(same(claims.get(a.assertion_id), a) for a in d.evidence))
        require(len({a.subject_key for a in m.assertions}) == 1)
        if d.status is ResolutionStatus.RESOLVED:
            require(len(self.matched_keys) == 1 and d.canonical_key == self.matched_keys[0])
        else:
            require(len(self.matched_keys) != 1 and d.canonical_key is None)

    @property
    def outcome_id(self) -> str:
        return "mention-resolution-v1:" + digest(self)


@dataclass(frozen=True)
class ResolvedOutput:
    previous: AssertedOutput
    candidates: CandidateSnapshot
    policy: ResolutionPolicyEvidence
    outcomes: tuple[MentionResolution, ...]
    canonicalized: tuple[CanonicalizedAssertion, ...]
    unlinked_assertion_ids: tuple[str, ...]
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.previous) is AssertedOutput
            and type(self.candidates) is CandidateSnapshot
            and type(self.policy) is ResolutionPolicyEvidence
            and type(self.provenance) is DecisionProvenance
        )
        require(
            same(self.candidates.scope, self.source.scope)
            and self.candidates.entity_type == self.policy.entity_type
            and self.candidates.identifier_namespace == self.policy.identifier_namespace
            and self.candidates.effective_at <= self.provenance.context.started_at
        )
        require(
            type(self.outcomes) is tuple
            and all(type(o) is MentionResolution for o in self.outcomes)
        )
        require(
            type(self.canonicalized) is tuple
            and all(type(c) is CanonicalizedAssertion for c in self.canonicalized)
        )
        require(type(self.unlinked_assertion_ids) is tuple)
        require(len(self.outcomes) == len(self.previous.mentions))
        require(len({m.mention_id for m in self.previous.mentions}) == len(self.previous.mentions))
        selected: dict[str, ResolutionDecision] = {}
        source_claims = {a.assertion_id: a for a in self.previous.assertions}
        for outcome, mention in zip(self.outcomes, self.previous.mentions, strict=True):
            require(
                same(outcome.mention, mention)
                and same(mention.scope, self.source.scope)
                and same(mention.observed_at, self.source.observed_at)
                and mention.entity_type == self.candidates.entity_type
            )
            require(all(same(source_claims.get(a.assertion_id), a) for a in mention.assertions))
            require(
                outcome.candidate_snapshot_id == self.candidates.snapshot_id
                and outcome.policy_reference == self.policy.reference.reference_id
                and same(outcome.decision.provenance, self.provenance)
                and all(key in self.candidates.keys for key in outcome.matched_keys)
            )
            if outcome.decision.status is ResolutionStatus.RESOLVED:
                for claim in mention.assertions:
                    require(claim.assertion_id not in selected)
                    selected[claim.assertion_id] = outcome.decision
        expected = tuple(
            CanonicalizedAssertion(
                a, selected[a.assertion_id], self.source.scope, self.provenance.context.started_at
            )
            for a in self.previous.assertions
            if a.assertion_id in selected
        )
        require(same(self.canonicalized, expected))
        require(
            self.unlinked_assertion_ids
            == tuple(
                a.assertion_id for a in self.previous.assertions if a.assertion_id not in selected
            )
        )
        require(self.provenance.policy_version == self.policy.reference.reference_id)

    @property
    def source(self) -> SourceReference:
        return self.previous.source

    @property
    def stage(self) -> StageId:
        return StageId.RESOLVE

    @property
    def input_ids(self) -> tuple[str, ...]:
        return resolution_input_ids(self.previous, self.candidates, self.policy)

    @property
    def batch_id(self) -> str:
        return "resolution-batch-v1:" + digest(
            (
                self.input_ids,
                self.outcomes,
                self.canonicalized,
                self.unlinked_assertion_ids,
                self.provenance,
            )
        )

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (
            self.batch_id,
            *(o.outcome_id for o in self.outcomes),
            *(o.decision.decision_id for o in self.outcomes),
            *(c.canonicalized_assertion_id for c in self.canonicalized),
        )

    @property
    def event(self):
        return event(
            "entity-resolution",
            self.provenance,
            self.input_ids,
            self.reference_ids,
            (self.previous.event.event_id,),
        )
