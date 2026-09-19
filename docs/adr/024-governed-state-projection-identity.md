# ADR-024: Governed state projection identity

Status: accepted

## Context

ADR-023 permits multiple competing approved BOM revisions to establish a required quantity when
their normalized values are exactly equal. ADR-020 requires every expected and observed state
record to carry a `StateScope`, including a version. A source revision cannot identify an
expected-state projection when more than one revision jointly governs it.

## Decision

Project a required quantity only after `procurement-governing-claims/v1` produces a governed
decision. An unresolved decision projects no `ExpectedRequirement`; it remains queryable through
its decision, candidate claims, dispositions, and evidence rather than becoming a zero quantity.

The projected scope keeps the request tenant, project, and site. Its version is the deterministic
`governed-required-quantity-scope` identifier computed from the policy ID, canonical item,
timezone-aware as-of time, and ordered governing claim IDs. This is a policy-decision identity,
not a source-revision identity. Source revision IDs remain on the governing decision and its
evidence paths.

Observed records that are compared to the projected requirement must use the same governed scope.
`ExpectedObservedState` continues to calculate outstanding quantity deterministically from these
typed records. It does not infer an expected requirement for an unresolved claim.

## Consequences

The reconciliation stage has an explicit, reproducible boundary before operational state. Equal
jointly governing revisions can supply one expected requirement without dropping either source.
Conflicting, stale, and unapproved claims remain inspectable and cannot silently enter arithmetic.
Adapters must carry the projected scope when they create corresponding observed state; they may
not substitute a source revision label for the policy-decision identity.
