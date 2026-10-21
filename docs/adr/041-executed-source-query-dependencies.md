# ADR-041: Capture dependencies from an executed source query

Status: accepted

Issue #220 follows ADR-040. A declared dependency graph cannot demonstrate that a producer actually
ran. The first adoption uses a small source-local query: distinct observed SKU strings in one exact
archived BOM. Canonical identity and governing quantities/prices remain separate policies; importing
the legacy reconciled demo pipeline would create a larger semantic bridge before those contracts.

A domain-owned frozen SourceSkuQuery derives values, diagnostics, evidence and reference identity
from an immutable DocumentSnapshot and explicit producer provenance. Known source strings are sorted
and deduplicated with the existing set/sort helper; all source rows remain separate dependency inputs.
A missing SKU makes the result unresolved/null, with known values labeled separately. Empty source
and unsupported cardinality fail typed rather than report an invented complete set.

The application loads the exact validated archive, executes the query, builds the real event/manifest
and registers through DependencyStore. Only SKU claims are data inputs, including unresolved ones.
Execution context and source/result identity are pinned; exact retries reproduce the result and keep
the first registered receipt/time. Returned query values are reproducible from retained inputs, not
persisted in a new cache. Existing generic graph registration remains a declaration, not attestation.

This is a source-level read/query producer, not adoption or bypass of the universal DERIVE stage's
OperationalState contract. No logical stage/topology, canonical entity or governing policy changes.
No original source/claim is rewritten and no approved correction is automatically applied.

Local context is caller-pinned and explicitly labeled, with fixed component/workflow/policy identity;
it is not production execution attestation. Authorization/portable-ID/context/time checks precede
storage I/O. Writes require existing trusted registrar REVIEW plus READ_EVIDENCE, reads exact scope.
The optional storage path is composed in bootstrap; no schema/old record-shape change or operational
agent authority is added. Source SKU corrections can now identify a real executed query reference;
global consumer coverage and controlled invalidation/recomputation remain subsequent work.
