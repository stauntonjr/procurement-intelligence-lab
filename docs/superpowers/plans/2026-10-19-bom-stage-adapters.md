# Shared BOM capture, structure and mapping plan

Issue #207; primary M1, parent #7. Implements ADR-022/017/019 and preserves later #31/#32/#33/#36 boundaries.

## Contract and architecture

Capture local bytes once through IngestStrategy into a content-addressed, injected port. A generic
XLSX StructureStrategy reads only verified captured bytes, recovers rows/cells with coordinates,
and assigns no procurement meaning. The procurement MapStrategy validates BOM headers and emits
raw MappedFields with evidence and missing/unmapped diagnostics. A three-stage application service
and bootstrap compose implementations and transformation events. An installed CLI exposes these
actual outputs; no planner/executor integration or later-stage success is inferred.

In-memory content retention is process-local. Exact scope, observation/capture times, run/code
identity and configuration digest remain explicit. Missing columns use retained row evidence;
blank/missing values become unresolved diagnostics, never zero. All numeric text stays raw.

## Tasks

1. Add failing tests for snapshot retention/integrity, generic structuring and domain mapping,
   including empty/header-only, sparse/reordered/duplicate coordinates, unsupported formats,
   missing/unmapped data, duplicate SKUs, cross-scope identity and timestamp boundaries.
2. Implement the content port/local adapters; extract shared XLSX mechanics without legacy behavior
   change and move C002's known-bad mutation to the shared mechanics file. Implement pure BOM mapping.
3. Add the application service, visible composition root and actual CLI with explicit JSON context;
   verify transformation input/output/parent edges and typed caller failures in subprocess tests.
4. Run hash-pinned deterministic conformance over synthetic XLSX sources, checking raw cells,
   row grouping, field/value recovery, locations, latency and zero inference cost separately.
5. Extend clean-wheel smoke, update ADR/status docs, run focused/full checks and all challenges,
   obtain exact-revision independent review and embed schema-valid semantic evidence in the PR.

## Review focus

- Never reopen a mutable source after capture; verify hash and byte length on captured-content reads.
- Duplicate/contradictory coordinates and unsupported formula/merged-cell variants fail typed.
- No schema mapping or numeric coercion in generic structure; no row dropped for an absent SKU.
- Strict CLI context typing/duplicate-key handling cannot replace absent evidence with success.
- Later planner stages, durable storage, authorization and full procurement extraction stay distinct.
