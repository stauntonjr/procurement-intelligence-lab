# ADR-047: Reconcile retained resolution producers under required-quantity policy

Status: accepted by owner approval of design `2c1b759768cfd577c3d9e4a589b655d390b46c9f` on 2026-10-24.
Approved plan24d20f0 is delivered through PR240 on main4591a0c, with the main receipt indexed by
PR241 at9818d09. [Issue #239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239)
and [main-delivery evidence](../development/evidence/issue-239/main-delivery.json) retain exact
protected delivery and bounded installed acceptance; broader M4 remains open.

## Context

PR237 delivers actual INGEST-through-RESOLVE execution and source-free retained evidence. The
bom-table package's later RECONCILE binding still names explicit-source-precedence, while accepted
ADR023/024 define predicate-specific approval/effectivity/supersession and policy-decision state
identity. A seventh executor must not silently substitute the older aggregate/source-order rule
for those ratified semantics.

## Decision

Adopt a distinct retained-resolution-reconciliation/v1 operation that consumes explicitly selected,
validated six-stage archive producers and invokes ReconcileStrategy exactly once for required
quantity. Its current receipt has RECONCILE succeeded and the other eleven stages not executed;
complete recorded producer receipts remain separate. It does not claim a fresh seven-stage prefix.

Use the existing procurement-governing-claims/v1 algorithm: eligible approved/effective BOM
revisions govern, exact-equal active values jointly govern, differing values abstain, and all
alternatives/evidence remain. Input authority metadata is a trusted local synthetic declaration,
not enterprise approval verification. It must be pinned to exact producer/source/revision identity;
no source label or time creates authority by itself.

First-profile inputs support at most one known nonnegative each-quantity per resolved item/revision.
Repeated item rows, unresolved identity, unknown/negative quantity and ambiguous duplicate source
membership are explicitly unsupported, preserving source recovery IDs. Identical content hashes
are duplicates even with different declared revision/approval IDs. Selected supersession pairs
with differing resolved item sets are unsupported; missing successor items never imply zero or
allow a predecessor value to survive through an unseen document-level supersession edge. No aggregation or implicit
conversion is invented. Null approval and policy-time ineligibility remain valid governed-policy
abstentions. Zero can govern; unresolved projects no state.

A new explicitly versioned operation/source profile binds the ratified policy; original bom-table
manifests, five/six-stage receipts/codecs/callers and local jobs remain unchanged. Governed state
uses ADR024 scope identity, exact governing evidence and UNKNOWN freshness; no observed procurement,
derived arithmetic, human review authority or external action is introduced.

A new opt-in archive capability retains result, policy/authority evidence and exact existing
producer-receipt links atomically, with source-free verified recovery and distinct current/first
retained receipts. It cannot import/recompute absent producers. New immutable records and a neutral
port keep procurement semantics outside adapters and platform runtime.

## Alternatives and consequences

Fresh multi-document seven-stage orchestration is deferred until its batch/receipt contract is
chosen. RESOLVE job-profile adoption remains a separate direction. Reusing a producer's historical
receipt is explicit and never a cache hit or new upstream invocation. This isolates authority
adoption from ingestion/orchestration and avoids changing the earlier delivered acceptance.

The [owner-approved design](../superpowers/specs/2026-10-24-retained-resolve-reconciliation-design.md)
contains bounds, type/error boundaries, evidence, public acceptance and required qualification.
Implementation [#239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239) follows the
[executable plan](../superpowers/plans/2026-10-24-retained-resolve-reconciliation.md), owner-approved at `24d20f0` on2026-10-24.
Design acceptance does not establish implementation or delivery on main.
