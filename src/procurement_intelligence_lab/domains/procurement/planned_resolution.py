"""Existing exact matching with explicit row evidence, namespace and abstention."""

from dataclasses import dataclass, replace
from datetime import datetime

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.domains.procurement.observation_assertions import (
    validate_bom_assertions,
)
from procurement_intelligence_lab.domains.procurement.resolution import (
    normalize_identifier,
    resolve_identifier,
)
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.platform.execution.contracts import validate_context
from procurement_intelligence_lab.platform.execution.identity import aware, same
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateInputEvidence,
    CandidateSnapshot,
    admit,
)
from procurement_intelligence_lab.platform.execution.resolution_outputs import (
    MentionResolution,
    ResolvedOutput,
)
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    EntityMention,
    ResolutionDecision,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def _catalog(candidates: CandidateSnapshot, policy: BomResolutionPolicy) -> None:
    admit(type(candidates) is CandidateSnapshot and type(policy) is BomResolutionPolicy)
    admit(
        candidates.entity_type == policy.entity_type
        and candidates.identifier_namespace == policy.identifier_namespace
    )
    admit(all(bool(normalize_identifier(key)) for key in candidates.keys))


def validate_bom_resolution_inputs(
    candidate_input: CandidateInputEvidence,
    policy: BomResolutionPolicy,
    *,
    scope: StateScope,
    as_of: datetime,
) -> None:
    admit(type(candidate_input) is CandidateInputEvidence)
    _catalog(candidate_input.snapshot, policy)
    aware(as_of)
    admit(
        same(scope, candidate_input.snapshot.scope)
        and candidate_input.snapshot.effective_at <= as_of
    )


def _mentions(
    mentions: tuple[EntityMention, ...],
    assertions: tuple[SourceAssertion, ...],
    candidates: CandidateSnapshot,
    provenance: DecisionProvenance,
) -> None:
    admit(type(mentions) is tuple and all(type(m) is EntityMention for m in mentions))
    admit(type(assertions) is tuple and all(type(a) is SourceAssertion for a in assertions))
    admit(
        type(provenance) is DecisionProvenance
        and provenance.component_kind is ComponentKind.DETERMINISTIC
    )
    validate_context(provenance.context)
    admit(candidates.effective_at <= provenance.context.started_at)
    observations: list[NormalizedObservation] = []
    for claim in assertions:
        admit(claim.context is not None)
        assert claim.context is not None
        o = claim.context.observation
        admit(same(o.scope, candidates.scope) and o.effective_at <= provenance.context.started_at)
        observations.append(o)
    try:
        validate_bom_assertions(tuple(observations), assertions, mentions)
    except SemanticContractError:
        raise PackageExecutionError(
            "resolution requires every original complete mention row"
        ) from None
    admit(
        all(
            same(m.scope, candidates.scope) and m.entity_type == candidates.entity_type
            for m in mentions
        )
    )


def _sku(mention: EntityMention) -> SourceAssertion:
    claims = tuple(
        c for c in mention.assertions if c.predicate.value == AssertionPredicate.HAS_SKU.value
    )
    admit(len(claims) == 1 and type(claims[0].value) is str and claims[0].value == mention.text)
    return claims[0]


def _matches(mention: EntityMention, candidates: CandidateSnapshot) -> tuple[str, ...]:
    value = normalize_identifier(mention.text)
    return tuple(key for key in candidates.keys if value and normalize_identifier(key) == value)


def _rationale(mention: EntityMention, matches: tuple[str, ...]) -> str:
    if not normalize_identifier(mention.text):
        return "invalid normalized identifier"
    if len(matches) == 1:
        return "normalized exact identifier match"
    return "ambiguous normalized candidate match" if matches else "no normalized candidate match"


@dataclass(frozen=True)
class BomResolve:
    candidates: CandidateSnapshot
    policy: BomResolutionPolicy

    def __post_init__(self) -> None:
        _catalog(self.candidates, self.policy)

    def resolve(
        self,
        mentions: tuple[EntityMention, ...],
        assertions: tuple[SourceAssertion, ...],
        *,
        provenance: DecisionProvenance,
    ) -> tuple[tuple[ResolutionDecision, ...], tuple[CanonicalizedAssertion, ...]]:
        _mentions(mentions, assertions, self.candidates, provenance)
        admit(provenance.policy_version == self.policy.reference_id)
        decisions: list[ResolutionDecision] = []
        by_claim: dict[str, ResolutionDecision] = {}
        for mention in mentions:
            decision = resolve_identifier(mention.text, self.candidates.keys, provenance=provenance)
            decision = replace(
                decision,
                evidence=(_sku(mention),),
                rationale=_rationale(mention, _matches(mention, self.candidates)),
            )
            decisions.append(decision)
            if decision.canonical_key is not None:
                for claim in mention.assertions:
                    admit(claim.assertion_id not in by_claim)
                    by_claim[claim.assertion_id] = decision
        links = tuple(
            CanonicalizedAssertion(
                a, by_claim[a.assertion_id], self.candidates.scope, provenance.context.started_at
            )
            for a in assertions
            if a.assertion_id in by_claim
        )
        return tuple(decisions), links

    def audit_decisions(
        self, mentions: tuple[EntityMention, ...], decisions: tuple[ResolutionDecision, ...]
    ) -> tuple[MentionResolution, ...]:
        admit(
            type(mentions) is tuple and type(decisions) is tuple and len(mentions) == len(decisions)
        )
        return tuple(
            MentionResolution(
                m,
                d,
                self.candidates.snapshot_id,
                _matches(m, self.candidates),
                self.policy.reference_id,
            )
            for m, d in zip(mentions, decisions, strict=True)
        )


def validate_bom_resolved_output(output: ResolvedOutput) -> None:
    try:
        admit(type(output) is ResolvedOutput)
        policy = BomResolutionPolicy.from_parameters(output.policy.parameters)
        admit(same(policy.evidence, output.policy))
        _catalog(output.candidates, policy)
        _mentions(
            output.previous.mentions,
            output.previous.assertions,
            output.candidates,
            output.provenance,
        )
        for outcome in output.outcomes:
            m, d = outcome.mention, outcome.decision
            matches = _matches(m, output.candidates)
            admit(outcome.matched_keys == matches and d.rationale == _rationale(m, matches))
            admit(same(d.evidence, (_sku(m),)))
            admit(d.canonical_key == (matches[0] if len(matches) == 1 else None))
    except (SemanticContractError, TypeError, AttributeError, KeyError):
        raise PackageExecutionContractError(
            "resolution output violates explicit SKU policy or row evidence"
        ) from None
