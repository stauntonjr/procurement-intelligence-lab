# Correction impact design

Issue #218, M2, parent #41; ADR-040. User-authorized continuation of the core architecture.

## Intent and scope
Identify potentially stale registered downstream references for an exact accepted document-value
correction without changing source assertions or choosing new truth. The graph records supplied
producer receipts, not verified executions or downstream values. Broader #13/#35/#37/#41/#56/#63
remain open. No numeric algorithm, new logical stage, automatic invalidation/recompute or UI.

## Inputs, output and policy
DependencyManifest(scope, request_id, recorder_id, roots, claims) is immutable. Roots are exact
(snapshot_id, assertion_id) pairs. Claims bind a reference_id to a supplied TransformationEvent
which produces it. Canonically ordered root/claim tuples have unique reference IDs; data inputs
must be roots or registered claims. USED_INPUT/DERIVED_FROM are data links; USED_SCHEMA/USED_MODEL
are retained metadata. Other relations are unsupported. Duplicate input edges, self/cyclic links,
missing inputs, root/output collisions, empty roots and excessive graphs fail contract validation.
Limit256 claims,128 roots,32 data inputs per producer; traversal depth1..32. Producer metadata is
portable fixed-offset/aware, bounded Unicode text, complete implementation/context identity; raw
environment entries are unsupported. Every producer pins nonempty input snapshot IDs from roots.
All metadata must be typed before any storage write.

DependencySnapshot binds the manifest, server recorded_at and policy declared-dependencies/v1.
Its identity uses scope/request ID and its full-content SHA256 includes all producer metadata.
Root/claim order is canonical; producer edge/output order retains original receipt identity.
A separate port append/get retains exact retries, fails changed commands, and checks source
membership. Explicit additive schema initialization; no archive/review rewrites or migration.

Impact requires exact scope/version, dependency snapshot ID, review task ID, aware as-of and depth.
Both dependency snapshot and APPROVE decision must be visible at as-of. Task source must match an
exact manifest root. Pending/rejected/future/missing/foreign inputs fail typed, never an empty
all-clear. BFS returns sorted affected reference IDs plus all declared links within the visited
subgraph, minimum depth per reference and omitted frontier. Shared descendants appear once.
Depth truncation is explicit; the graph itself remains closed/acyclic. Coverage always says
registered_graph_only; global completeness not_evaluated even if traversal is complete. Reports
include source evidence, previous/proposed typed values, exact task/decision/snapshot IDs/digests,
policy and as-of. Read-only impact never marks actual downstream state or computes a new value.

## Authority and public boundary
Core dataclasses/Protocol are framework-independent. Composition injects archive, review journal,
dependency store and clock. Registration requires REVIEW and READ_EVIDENCE before I/O; inspection
requires READ_EVIDENCE and matching request scope. Separate CLI init/register/inspect reads recorder
identity only from PIL_DOCUMENT_REVIEWER_ID, uses the existing DSN and exact scope file, and accepts
registered typed DAG JSON produced by the SDK codec. The boundary never accepts a client recorder
or recording time; supplied producer execution metadata is a declaration, not the recorder clock.
CLI emits sanitized JSON/exit2 for bad graphs, unavailable storage and authorization failures.
No operational-agent tool or production identity service is added.

## Evidence and verification
Core scenario tests include empty downstream graph, one/many/diamond, duplicates/cycles/missing,
reorder/replay, null/zero correction compatibility, scope/time/future/depth boundaries. Real isolated
Postgres covers atomic registration, concurrent retries, conflicts, restart/integrity and SQL guards.
Actual subprocess CLI and clean installed wheel run archive/source deletion -> human correction ->
declared producer fixture -> registration -> restarted bounded impact; producer fixtures are labeled
and never promoted into runtime producer adoption. Full check/ratchet,30 compatibility challenges,
latest-revision independent semantic/architecture review and validated PR evidence are required.
