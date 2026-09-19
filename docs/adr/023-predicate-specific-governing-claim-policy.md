# ADR-023: Predicate-specific governing-claim policy

Status: accepted

## Context

The assertion ledger preserves what sources said, while reconciliation determines whether a value
can govern a scoped procurement answer. Issues #15, #38, and #46 require that determination to
be deterministic, inspectable, time-aware, and separate from model output. The local showcase
needs a policy-backed conflicting-revision example without treating newer document or ingestion
time as authority.

## Decision

Adopt [`procurement-governing-claims/v1`](../product/governing-claim-policy-v1.md) as the
versioned procurement reconciliation policy. A decision takes explicit predicate, canonical item,
tenant/project/site scope, and as-of time. It retains every candidate assertion and reports the
policy ID, eligibility dispositions, governing assertion IDs, and evidence locations.

Eligibility uses approved authority, predicate-specific source type, matching scope, and an
effective interval that contains the query as-of time. Approval must be present no later than the
query as-of time. Document time and ingestion time remain provenance only; they never select a
winner. Effective intervals are start-inclusive and end-exclusive.

For required quantity, an approved BOM revision is eligible only when it is effective at the
query as-of time. A revision supersedes another only through explicit supersession evidence.
Competing eligible approved revisions with the same normalized required quantity and unit
establish that value jointly: each matching assertion is retained as governing evidence and the
decision records the shared-value disposition. Competing eligible revisions with different values
remain unresolved and the public answer abstains.

Ordered quantity, planned/committed price, expected delivery, and observed delivery use their
predicate-specific authority rules in the policy. Expected requirements and observed procurement
state remain separate projections under ADR-020.

## Consequences

Reconciliation implementation must accept policy identity and all required temporal, approval,
scope, revision, and source fields explicitly. It must fail closed for missing metadata, uncovered
predicates, unsupported unit conversion, ambiguous authority, and conflicting values. Equal
competing values are not silently de-duplicated: their multiple governing evidence paths remain
visible.

This ADR does not itself implement the policy, approve a source record, select a real procurement
claim, or complete Issues #15, #38, or #46. Implementations must add a frozen fixture, contract
tests, decision provenance, and browser evidence against this policy version.
