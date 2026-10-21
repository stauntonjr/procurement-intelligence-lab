# Correction impact implementation plan

Use executing-plans inline, TDD, and one fresh-context whole-branch review.
Spec: ../specs/2026-10-20-correction-impact-design.md; ADR-040; Issue #218.

## Review focus
Missing coverage is never all-clear; only data edges propagate impact; exact source/review/scope/time
binding; hashes include all producer metadata; failed/conflicting writes leave no partial graph.

## Tasks
1. Core dependencies.py: frozen roots/claims/manifest/snapshot/impact records, strict intrinsic
   validity, content digest and bounded BFS. Unit RED/GREEN for seven semantic scenario families.
2. ports/dependencies.py and additive Postgres adapter: explicit init, exact source membership,
   retry/conflict/rollback, hashes/typed replay. Real isolated Postgres contract RED/GREEN.
3. Application/CLI/bootstrap: explicit authority and injected clock, exact approved correction
   binding/as-of, strict typed producer input and output. Actual public parser/subprocess RED/GREEN.
4. Clean wheel probe and absent-driver smoke, public contract/README/handoff/milestone sync.
   Seal source; full check/coverage, package and30 compatibility challenges; one independent latest-
   revision semantic/architecture review. Resolve findings with regression evidence.
5. Publish validated revision-bound PR evidence, green required checks, merge; verify main tree and
   real caller, close218 only, reconcile Project and audit, record advisory provider result.

## Execution record
Design choices: declared receipt graph instead of fabricated downstream calculations or graph DB;
no automatic recomputation. Existing snapshot/review contracts remain compatible. User's proceed
continues the established inline delivery loop. Qualification/review/merge evidence belongs in the
revision-bound PR and Issue closeout, not in an unversioned chat transcript.
