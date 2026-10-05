# ADR-034: Prospective human reconciliation

Status: accepted for the M9/#74 reconciliation-review continuation.

An authenticated procurement reviewer may resolve an eligible required-quantity conflict for one
exact item + project + site scope. The choice never establishes document-wide precedence. The
application, not the browser or model, owns identity, scope, candidate eligibility and the
server-owned `effective_at` timestamp.

The reviewer may select one of exactly two eligible conflicting required-quantity claims, keep the
scope unresolved, confirm the assessment without changing governed state, or mark the assessment
as needing correction. Selecting a governing claim or keeping the conflict unresolved requires a
required rationale. Both governing and losing assertions, their dispositions and all evidence are
retained.

The decision is prospective: `recorded_at` and `effective_at` are the same server-generated aware
time in this version. Earlier as-of state, facts, anomalies and decisions are not rewritten.
Caller-supplied or retroactive effective times are unsupported and fail closed. A later authorized
decision may supersede the current decision prospectively.

The application validates the active assessment digest, exact candidate set, evidence, authority
and scope before an atomic durable write. Exact replay is idempotent; changed choice, rationale,
candidate membership or evidence conflicts. A reconciliation decision may update later operational
state and derived discrepancy assessment, but it cannot trigger a purchase or any external action.

Models may explain or route the review. They cannot select a governing revision, supply the
rationale, or receive reconciliation authority. Domain records remain framework-independent;
SQLite and HTTP remain replaceable adapters.
