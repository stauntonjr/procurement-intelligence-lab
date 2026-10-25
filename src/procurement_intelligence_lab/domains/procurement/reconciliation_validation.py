"""Independent source admission and pure recorded governing-output postconditions."""

from datetime import datetime
from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.domains.procurement.governance import GoverningClaimStatus
from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    BomReconciliationPolicy,
    load_bom_authority,
)
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.domains.procurement.retained_reconciliation import (
    build_reconciliation_audit,
    candidates,
    policy_decisions,
)
from procurement_intelligence_lab.platform.execution.identity import aware, same
from procurement_intelligence_lab.platform.execution.outputs import require
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    SemanticContractError,
    UnsupportedReconciliationInputError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.reconciliation import ReconciliationStatus
from procurement_intelligence_lab.platform.semantics.resolution import CanonicalizedAssertion
from procurement_intelligence_lab.platform.semantics.state import StateFreshness


def supported(condition: bool) -> None:
    if not condition:
        raise UnsupportedReconciliationInputError(
            "retained producers are outside the supported required-quantity profile"
        )


def validate_bom_reconciliation_inputs(
    inputs: RetainedReconciliationInputs, *, started_at: datetime
) -> None:
    admit(type(inputs) is RetainedReconciliationInputs)
    aware(started_at)
    admit(inputs.as_of <= started_at)
    BomReconciliationPolicy(inputs.policy)
    authority = load_bom_authority(inputs.authority.raw_json)
    admit(same(authority.evidence, inputs.authority))
    records = {r.execution_digest: r for r in authority.records}
    admit(set(records) == {p.completed.execution_digest for p in inputs.recorded_producers})
    item_sets: dict[str, set[str]] = {}
    for p in inputs.recorded_producers:
        r = records[p.completed.execution_digest]
        a = p.completed.prefix.snapshot.artifact
        admit(
            r.artifact_id == a.artifact_id
            and r.content_hash == a.content_hash
            and a.captured_at <= started_at
        )
        o = p.completed.execution.output
        admit(same(BomResolutionPolicy.from_parameters(o.policy.parameters).evidence, o.policy))
        supported(not o.unlinked_assertion_ids)
        items = {c.canonical_key for c in o.canonicalized}
        quantities: dict[str, list[CanonicalizedAssertion]] = {key: [] for key in items}
        for c in o.canonicalized:
            if c.assertion.predicate.value == AssertionPredicate.HAS_QUANTITY.value:
                claim = c.assertion
                supported(claim.context is not None and type(claim.value) is Decimal)
                assert claim.context is not None and isinstance(claim.value, Decimal)
                supported(
                    claim.value.is_finite()
                    and claim.value >= 0
                    and claim.context.observation.unit == "each"
                    and claim.context.observation.status is EpistemicStatus.OBSERVED
                )
                quantities[c.canonical_key].append(c)
        supported(all(len(q) == 1 for q in quantities.values()))
        item_sets[r.revision_id] = items
    for r in authority.records:
        for previous in r.supersedes_revision_ids:
            if previous in item_sets:
                supported(item_sets[previous] == item_sets[r.revision_id])


def validate_bom_reconciliation_output(output: ReconciledOutput) -> None:
    try:
        validate_bom_reconciliation_inputs(
            output.inputs, started_at=output.provenance.context.started_at
        )
        policy = policy_decisions(output.inputs)
        require(len(output.decisions) == len(policy))
        links = {c.claim_id: a for c, a in candidates(output.inputs)}
        states = {s.subject_key: s for s in output.states}
        require(set(states) == {d.canonical_key for d in policy if d.governing})
        for actual, expected in zip(output.decisions, policy, strict=True):
            governed = expected.status is not GoverningClaimStatus.UNRESOLVED
            require(
                actual.subject_key == expected.canonical_key
                and actual.policy_id == expected.policy_id
            )
            require(
                actual.status
                is (
                    ReconciliationStatus.RECONCILED if governed else ReconciliationStatus.UNRESOLVED
                )
            )
            require(same(actual.governing, tuple(links[c.claim_id] for c in expected.governing)))
            require(same(actual.losing, tuple(links[c.claim_id] for c in expected.losing)))
            require(actual.rationale == "required quantity: " + expected.status.value)
            require(same(actual.provenance, output.provenance))
            if not governed:
                continue
            state = states[actual.subject_key]
            required_version = stable_id(
                "governed-required-quantity-scope",
                expected.policy_id,
                expected.canonical_key,
                output.inputs.as_of.isoformat(),
                tuple(c.claim_id for c in expected.governing),
            )
            scope = output.inputs.scope
            require(
                (
                    state.scope.tenant_id,
                    state.scope.project_id,
                    state.scope.site_id,
                    state.scope.version,
                )
                == (scope.tenant_id, scope.project_id, scope.site_id, required_version)
            )
            evidence = tuple(
                {c.evidence.evidence_id: c.evidence for c in expected.governing}.values()
            )
            require(
                state.freshness is StateFreshness.UNKNOWN
                and state.reconciliation_id == actual.reconciliation_id
            )
            require(
                same(state.as_of, output.inputs.as_of) and same(state.provenance, output.provenance)
            )
            require(same(state.evidence, evidence) and len(state.attributes) == 1)
            attr = state.attributes[0]
            require(
                attr.name == "required_quantity"
                and type(attr.value) is Decimal
                and attr.value == expected.value
            )
            require(
                attr.unit == "each"
                and attr.status is EpistemicStatus.OBSERVED
                and same(attr.evidence, evidence)
            )
        require(
            output.domain_audit
            == build_reconciliation_audit(
                output.inputs, output.decisions, output.states, provenance=output.provenance
            )
        )
        outside = tuple(
            sorted(
                a.assertion_id
                for p in output.inputs.recorded_producers
                for a in p.completed.execution.output.previous.assertions
                if a.predicate.value != AssertionPredicate.HAS_QUANTITY.value
            )
        )
        require(output.outside_predicate_ids == outside)
    except SemanticContractError:
        raise PackageExecutionContractError(
            "recorded required-quantity output violates source and governing-policy bindings"
        ) from None
