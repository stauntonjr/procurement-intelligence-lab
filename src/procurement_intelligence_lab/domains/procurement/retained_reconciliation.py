"""Existing governing policy adopted through the neutral ReconcileStrategy port."""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import cast

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimDecision,
    GoverningClaimStatus,
    GoverningPredicate,
    GoverningSourceType,
    reconcile_required_quantity,
)
from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    load_bom_authority,
)
from procurement_intelligence_lab.platform.execution.identity import canonical, encoded, same
from procurement_intelligence_lab.platform.execution.outputs import require
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.reconciliation import (
    ReconciliationDecision,
    ReconciliationStatus,
)
from procurement_intelligence_lab.platform.semantics.resolution import CanonicalizedAssertion
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.platform.semantics.state import (
    OperationalState,
    StateAttribute,
    StateFreshness,
)


def quantity_assertions(inputs: RetainedReconciliationInputs) -> tuple[CanonicalizedAssertion, ...]:
    return tuple(
        sorted(
            (
                a
                for p in inputs.recorded_producers
                for a in p.completed.execution.output.canonicalized
                if a.assertion.predicate.value == AssertionPredicate.HAS_QUANTITY.value
            ),
            key=lambda a: a.canonicalized_assertion_id,
        )
    )


def candidates(
    inputs: RetainedReconciliationInputs,
) -> tuple[tuple[GoverningClaim, CanonicalizedAssertion], ...]:
    authority = {
        r.execution_digest: r for r in load_bom_authority(inputs.authority.raw_json).records
    }
    result: list[tuple[GoverningClaim, CanonicalizedAssertion]] = []
    for p in inputs.recorded_producers:
        r = authority[p.completed.execution_digest]
        for a in p.completed.execution.output.canonicalized:
            if a.assertion.predicate.value != AssertionPredicate.HAS_QUANTITY.value:
                continue
            claim = a.assertion
            assert claim.context is not None
            c = GoverningClaim(
                stable_id(
                    "retained-required-quantity-claim-v1",
                    p.completed.execution_digest,
                    a.canonicalized_assertion_id,
                    inputs.authority.semantic_digest,
                    inputs.policy.reference.reference_id,
                ),
                a.canonical_key,
                GoverningPredicate.REQUIRED_QUANTITY,
                cast(Decimal, claim.value),
                "each",
                r.source_role,
                inputs.scope,
                claim.evidence,
                r.revision_id,
                r.supersedes_revision_ids,
                r.approved_at,
                r.effective_from,
                r.effective_until,
                r.document_at,
                p.completed.prefix.snapshot.artifact.captured_at,
            )
            result.append((c, a))
    return tuple(sorted(result, key=lambda pair: pair[0].claim_id))


def eligibility_reason(c: GoverningClaim, as_of: datetime) -> str | None:
    if c.source_type is not GoverningSourceType.APPROVED_BOM_REVISION:
        return "wrong_source_role"
    if c.approved_at is None:
        return "unapproved"
    if c.approved_at > as_of:
        return "approval_after_as_of"
    if c.effective_from > as_of:
        return "not_yet_effective"
    if c.effective_until is not None and as_of >= c.effective_until:
        return "expired"
    return None


def policy_decisions(inputs: RetainedReconciliationInputs) -> tuple[GoverningClaimDecision, ...]:
    cs = tuple(c for c, _ in candidates(inputs))
    ctx = RequestContext(
        "synthetic-local-reconciliation",
        inputs.scope.tenant_id,
        inputs.scope.project_id,
        inputs.scope.site_id,
        frozenset({Permission.READ_STATE}),
        "retained-required-quantity",
    )
    result: list[GoverningClaimDecision] = []
    for key in sorted({c.canonical_key for c in cs}):
        relevant = tuple(c for c in cs if c.canonical_key == key)
        d = reconcile_required_quantity(
            relevant, canonical_key=key, request_context=ctx, as_of=inputs.as_of
        )
        eligible = tuple(c for c in relevant if eligibility_reason(c, inputs.as_of) is None)
        dispositions: list[tuple[str, str]] = []
        for c in (*d.governing, *d.losing):
            reason = eligibility_reason(c, inputs.as_of)
            if reason is None:
                if any(
                    c.revision_id in successor.supersedes_revision_ids
                    and successor.claim_id != c.claim_id
                    for successor in eligible
                ):
                    reason = "superseded"
                elif c in d.governing:
                    reason = "governing"
                else:
                    reason = "conflicting_active_value"
            dispositions.append((c.claim_id, reason))
        result.append(replace(d, dispositions=tuple(dispositions)))
    return tuple(result)


def neutral_projection(
    inputs: RetainedReconciliationInputs,
    domain: tuple[GoverningClaimDecision, ...],
    provenance: DecisionProvenance,
) -> tuple[tuple[ReconciliationDecision, ...], tuple[OperationalState, ...]]:
    links = {c.claim_id: a for c, a in candidates(inputs)}
    decisions: list[ReconciliationDecision] = []
    states: list[OperationalState] = []
    for d in domain:
        governed = d.status is not GoverningClaimStatus.UNRESOLVED
        neutral = ReconciliationDecision(
            d.canonical_key,
            ReconciliationStatus.RECONCILED if governed else ReconciliationStatus.UNRESOLVED,
            tuple(links[c.claim_id] for c in d.governing),
            tuple(links[c.claim_id] for c in d.losing),
            d.policy_id,
            "required quantity: " + d.status.value,
            provenance,
        )
        decisions.append(neutral)
        if not governed:
            continue
        evidence = tuple({c.evidence.evidence_id: c.evidence for c in d.governing}.values())
        scope = replace(
            inputs.scope,
            version=stable_id(
                "governed-required-quantity-scope",
                d.policy_id,
                d.canonical_key,
                inputs.as_of.isoformat(),
                tuple(c.claim_id for c in d.governing),
            ),
        )
        states.append(
            OperationalState(
                d.canonical_key,
                scope,
                inputs.as_of,
                StateFreshness.UNKNOWN,
                (
                    StateAttribute(
                        "required_quantity", d.value, EpistemicStatus.OBSERVED, evidence, "each"
                    ),
                ),
                evidence,
                provenance,
                neutral.reconciliation_id,
            )
        )
    return tuple(decisions), tuple(states)


def build_reconciliation_audit(
    inputs: RetainedReconciliationInputs,
    decisions: tuple[ReconciliationDecision, ...],
    states: tuple[OperationalState, ...],
    *,
    provenance: DecisionProvenance,
) -> bytes:
    ds = policy_decisions(inputs)
    expected = neutral_projection(inputs, ds, provenance)
    require(same(decisions, expected[0]) and same(states, expected[1]))
    mapping = {c.claim_id: a for c, a in candidates(inputs)}
    authority = load_bom_authority(inputs.authority.raw_json)
    return canonical(
        {
            "schema": "procurement-required-quantity-audit/v1",
            "policy_id": inputs.policy.reference.reference_id,
            "source_scope": encoded(inputs.scope),
            "as_of": inputs.as_of.isoformat(),
            "authority": encoded(authority.records),
            "items": tuple(
                {
                    "decision": encoded(d),
                    "domain_decision_id": d.decision_id,
                    "neutral_decision_id": n.reconciliation_id,
                    "basis": "reconciled" if d.governing else None,
                    "candidates": tuple(
                        {
                            "claim_id": c.claim_id,
                            "canonicalized_assertion_id": mapping[
                                c.claim_id
                            ].canonicalized_assertion_id,
                            "source_assertion_id": mapping[c.claim_id].assertion.assertion_id,
                        }
                        for c in (*d.governing, *d.losing)
                    ),
                }
                for d, n in zip(ds, decisions, strict=True)
            ),
            "outside_predicate_ids": tuple(
                sorted(
                    a.assertion_id
                    for p in inputs.recorded_producers
                    for a in p.completed.execution.output.previous.assertions
                    if a.predicate.value != AssertionPredicate.HAS_QUANTITY.value
                )
            ),
        }
    )


@dataclass(frozen=True)
class BomRetainedReconcileStrategy:
    inputs: RetainedReconciliationInputs

    def reconcile(
        self,
        assertions: tuple[CanonicalizedAssertion, ...],
        *,
        scope: StateScope,
        as_of: datetime,
        provenance: DecisionProvenance,
    ) -> tuple[tuple[ReconciliationDecision, ...], tuple[OperationalState, ...]]:
        from procurement_intelligence_lab.domains.procurement.reconciliation_validation import (
            validate_bom_reconciliation_inputs,
        )

        validate_bom_reconciliation_inputs(self.inputs, started_at=provenance.context.started_at)
        require(
            same(assertions, quantity_assertions(self.inputs))
            and same(scope, self.inputs.scope)
            and same(as_of, self.inputs.as_of)
        )
        return neutral_projection(self.inputs, policy_decisions(self.inputs), provenance)
