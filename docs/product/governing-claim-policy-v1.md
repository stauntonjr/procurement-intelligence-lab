# Procurement governing-claim policy v1

**Policy ID:** `procurement-governing-claims/v1`

**Status:** ratified on 2026-09-18
**Governing work:** Issues #15, #38, and #46; ADR-023

This policy selects governed procurement claims after entity resolution. It applies to synthetic
showcase fixtures first and is deliberately explicit enough to become versioned configuration.
It does not turn an assertion, extraction result, or model output into authority by itself.

## Required decision input

Each candidate must provide a canonical item and predicate, tenant/project/site scope, source
type, source assertion and evidence IDs, normalized value and unit/basis, document time,
ingestion time, effective interval, revision identity where applicable, and approval/review record.
An observed-delivery candidate must also provide observed time. A query must provide the predicate,
canonical item, tenant/project/site, and timezone-aware as-of time.

Missing required metadata yields an explicit ineligible or unresolved disposition. It never falls
back to a source filename, document order, revision label, or ingestion order.

## Common eligibility and timing rules

1. Match the query predicate, canonical item, and full tenant/project/site scope.
2. Require the source type and approval state listed for that predicate below.
3. Require approval at or before the query as-of time.
4. Require the effective interval to contain the query as-of time. An interval begins inclusively
   and ends exclusively; an absent end is open-ended.
5. Retain document time and ingestion time as provenance. Neither is a precedence rule.
6. Retain every rejected, stale, superseded, conflicting, and unresolved assertion with its
   disposition and evidence.

An explicit approved supersession relation ends the superseded revision's eligibility when its
successor becomes effective. A larger revision number, newer document date, or later ingestion
cannot establish supersession.

## Predicate rules

| Predicate and answer basis | Eligible authority | Governing rule | Failure behavior |
|---|---|---|---|
| Required quantity | Approved BOM revision | Select eligible BOM revision(s) using explicit effective/supersession evidence. If competing eligible revisions have the same normalized quantity and unit, use that shared value and retain all of them as jointly governing. | Different competing values, missing approval/effectivity/supersession evidence, or unsupported unit conversion yields an abstention. |
| Ordered quantity | Approved PO line | Sum only separately identified approved PO lines that are in scope and effective. A PO never changes the required quantity. | Ambiguous identity, scope, approval, or duplicate-line relationship yields an abstention for the affected quantity. |
| Planned unit price | Accepted supplier quote | Use an eligible accepted quote with declared currency, price basis, and effective interval. | Missing currency/basis, multiple incompatible eligible quotes, or no accepted quote yields an abstention. |
| Committed unit price | Approved PO line | Use an eligible PO line with declared currency, price basis, and effective interval. | Missing currency/basis or incompatible eligible PO values yields an abstention. |
| Expected delivery | Supplier-confirmed commitment linked to the applicable approved PO line | Use the eligible commitment effective at the query time. A replacement requires explicit confirmation/supersession evidence. | Competing commitments or missing confirmation yields an abstention. |
| Observed delivery | Receipt or inspection observation | Use eligible observed events at or before query as-of time to determine observed state. Observed state remains distinct from expected requirement. | Missing identity, scope, or observation evidence yields unknown observed state, never zero. |

The caller must request a price basis (`planned` or `committed`). The policy does not silently
substitute a quote for a purchase-order price, or vice versa.

## Equal-value competing approved revisions

When two or more otherwise competing eligible approved BOM revisions assert the same normalized
required quantity and unit for the same scoped canonical item, the quantity is established. The
decision records:

- status `governed_shared_value`;
- the shared normalized quantity and unit;
- every matching assertion as governing evidence;
- the unresolved relationship between revisions, if no explicit supersession relation exists;
- policy ID/version and the as-of query context.

This exception applies only to exact equality after an already-supported normalization. The policy
does not introduce a new unit-conversion or tolerance rule. Different values remain `unresolved`,
with no applicable quantity returned.

## Required decision output

Every result records the policy ID/version, scope and as-of key, predicate and answer basis,
eligible candidates, governing and losing assertion IDs, dispositions and reasons, selected value
or explicit abstention, and all EvidenceRefs. A public explanation may summarize this decision but
must not select authority or arithmetic in the browser or a model.

For required quantity, a governed decision projects a typed `ExpectedRequirement`; an unresolved
decision projects none. The projection has a deterministic policy-decision scope identity so that
equal jointly governing revisions do not force an arbitrary source revision into operational state.
See [ADR-024](../adr/024-governed-state-projection-identity.md).

## Showcase acceptance examples

1. Revision A requires 4 GPUs and revision B requires 6; both are approved and effective without
   explicit supersession. The required quantity abstains and shows both sources.
2. Revision B explicitly supersedes A and is effective at the query as-of time. The required
   quantity is 6, with A retained as superseded evidence.
3. Revision A and B are competing, approved, and effective but both require 4 GPUs. The required
   quantity is 4 with `governed_shared_value` and both evidence paths displayed.
4. Revision B has no approval record. It cannot govern, regardless of revision label or ingestion
   time.
5. A PO for 2 GPUs and an approved BOM requirement of 4 expose ordered 2 and required 4 as
   different predicates; outstanding quantity is a separately evidenced deterministic derivation.
