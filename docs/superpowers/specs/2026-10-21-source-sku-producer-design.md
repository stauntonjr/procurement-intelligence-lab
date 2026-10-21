# Executed archived BOM source-SKU producer

Issue #220, M2 parent #35, ADR-041. Authorized continuation after dependency foundation #218.

## Intent
Replace fixture-only producer proof with one real synchronous query whose dependencies can be
inspected after an approved source correction. Keep source strings separate from canonical identity,
current requirement, pricing and state. No automatic invalidation/recomputation or new logical stage.

## Domain contract
SourceSkuQuery(snapshot, provenance) is frozen, domain-owned and intrinsic: exact DocumentSnapshot,
validated BOM assertions/profile, fixed deterministic component/version/policy, complete portable
context pinned to that snapshot, started_at at or after source recording. There must be1..128 SKU
claims, each retaining exact typed source context/evidence; missing/blank values stay unresolved.
The sorted/deduplicated source string tuple uses the same helper as existing distinct_skus. Complete
inputs yield observed source-set value; any unknown yields null/unresolved and separately labeled
known_skus/missing_assertion_ids. No description/quantity/price contributes to this query.

Reference identity binds snapshot, every SKU input, result/status/policy and full execution digest
(including context time/parent metadata). A real source-sku-set-query TransformationEvent lists each
SKU assertion as USED_INPUT and emits that reference. Manifest roots/claims are canonical and use
existing immutable schemas/ports. Header-only/oversize/type/Unicode/foreign metadata fail typed.

## Application and authority
ArchivedBomQueryService injects validated archive reader, producer callable, DependencyStore and
clock. execute(scope,snapshot_id,request_id,execution,context) authorizes REVIEW+READ_EVIDENCE and
matching resource scope, validates all IDs/principal/scope/context and aware fixed-offset clock
before I/O, rejects future producer time, loads the exact archive, executes producer and registers
its event/roots. No partial-success output on failure. Context time must follow source recording.
Full source/metadata/request/actor replay returns the original dependency receipt/time; changed
reused identity conflicts. Result is recomputed from the immutable source on each explicit call,
not served from a new result store. Registration still states registered_graph_only/global unknown.

## Public boundary
interfaces.archived_bom_query requires --scope/--snapshot-id/--request-id/--context. Context is strict
UTF8 JSON with exactly run_id/code_revision/started_at, bounded32KiB, duplicate/depth/type checks.
The composition boundary fixes source pin, workflow/version, local image identity, config digest
and no raw environment. Caller-pinned local metadata is not production attestation. Recorder is
PIL_DOCUMENT_REVIEWER_ID only, DSN existing private configuration. Argparse errors and malformed
values map to sanitized JSON exit2. Existing archive/review/dependency schemas and callers unchanged.

## Evidence and boundaries
Actual CLI capture -> source deletion -> real producer -> persisted dependency -> restart/replay ->
exact human SKU correction -> impact returns that query reference. Approving a proposed SKU does
not change the original query output/source. A non-SKU correction has no registered root in this
producer manifest; the existing impact API fails not-found, not a global unaffected assertion.
Core cases include order/duplicate/unknown/empty/one/many/128boundaries; malformed IDs/context/time
and permissions before I/O; real PG retry/conflict/unavailable and unchanged original records.
Clean built artifact must run the real producer. Full check/ratchet and30 challenges, one fresh-context
whole-branch semantic/architecture review and exact-revision PR evidence are required. Other source
queries, real governed/state/derived producers, general EvidenceTrace, producer result persistence,
production identity/UI/HA/deployment and controlled recomputation remain open under broader Issues.
