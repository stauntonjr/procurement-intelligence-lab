# Archived source-SKU producer plan

Execute inline with TDD and one fresh-context whole-branch review.
Spec: ../specs/2026-10-21-source-sku-producer-design.md; ADR-041; Issue #220.

## Review focus
Never label source strings canonical; missing SKU never becomes complete/empty/zero; all duplicate
rows remain distinct roots; metadata/digest and temporal/source pins must survive exact replay;
a correction identifies the actual produced reference without being applied or recomputed.

1. Domain producer and shared deterministic set/sort helper; unit RED/GREEN for intrinsic source,
   provenance, set/unknown/empty/cardinality and old distinct_skus compatibility. Add typed error.
2. Authorized application composition with injected producer/clock/ports; real Postgres RED/GREEN
   registration/retry/conflict/restart and fail-before-I/O boundaries. Preserve old schemas/wires.
3. Actual CLI/context/parser/subprocess RED/GREEN. Real producer -> SKU correction -> impact oracle;
   extend clean wheel missing-driver and installed storage probe; docs/README/handoff/milestone sync.
4. Seal source; full make check/coverage ratchet, package smoke,30 compatibility challenges; independent
   latest-head review and regressions for concrete findings. Publish validated revision-bound evidence.
5. Required hosted gates green, merge, verify identical main tree plus actual caller; close220 only,
   reconcile Project, run deterministic planning audit and record advisory provider result.

## Decisions
Use one source-local existing set calculation rather than introducing canonical identity/pricing or
a new result store. Producer values are replayed from the immutable archive, with durable dependency
receipts only. User's proceed continues the established inline delivery loop; implementation and
review evidence are retained in PR/Issue closeout rather than transient conversation.

The direct producer is bounded to32 SKU inputs by the existing per-event data-input contract,
which is stricter than the128-root manifest bound. Larger inputs fail before registration; this
slice does not invent batching or silently truncate dependencies.
