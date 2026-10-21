# Controlled reviewed-SKU replay implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute a new source-SKU view over explicitly selected approved corrections with honest data lineage, immutable retries and installed-CLI acceptance.

**Architecture:** Extend the neutral dependency graph with validated correction roots. Add an explicitly initialized correction-root storage capability alongside existing schema1; execute row-application and set-query producers through an injected application service. Keep the original source query and governing state unchanged.

**Tech Stack:** Python stdlib frozen dataclasses/Protocols, existing SemanticCodec and optional psycopg/Postgres; pytest, existing wheel smoke and challenge harness. No new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-10-21-reviewed-sku-replay-design.md` (maintainer approved 2026-10-21); ADR-042; decision Issue #222, implementation #223. Baseline main `a26d61510622121570a5eefbf8b056451601264b`.

## Global Constraints

- Policy `selected-reviewed-source-skus/v1`; exact scope/version/source, explicit inclusive as-of, 1..32 distinct selected approved task IDs.
- Preserve source rows, case variants, original source/query values and review history; unknown/null never becomes zero or a complete subset.
- Reject conflicting selected tasks for one assertion, including equal proposals. No latest-winner, unselected-review or globally fresh claim.
- At most32 source roots plus32 correction roots,33 producer references, and32 data inputs per producer; no truncation.
- Require REVIEW plus READ_EVIDENCE before I/O; source/approval <= as-of <= execution <= registration, with a fresh post-computation clock sample.
- Exact retries bind source/selection/as-of/context/request/actor and retain the first receipt/time; changed reused commands conflict atomically.
- Preserve old wire shapes/readability; initialize capability explicitly. No automatic migrations, new result cache, operational tool, canonical/governing state or universal-stage change.

## Review Focus

1. Equal-valued foreign enums and malformed tuples must fail intrinsically, before I/O where possible (Tasks1/3/4).
2. Changed as-of or equal-instant/different-offset context must not alias an existing request (Tasks3/4).
3. Missing/corrupt review-root capability must fail closed while archive-only schema1 operations remain usable (Task2).
4. Correct one duplicate-token row only; selected null and unselected missing rows remain unresolved (Task3).
5. All32 corrected rows need intermediate producers; no event may silently acquire64 inputs (Tasks1/3).

---

## File and interface map

- `platform/semantics/dependencies.py`: neutral `ApprovedCorrectionRef` and `DependencyRoot` union, common root IDs, graph invariants. No procurement imports.
- `adapters/postgres_dependency_corrections.py`: additive capability DDL/probe and journal-root verification helpers; `adapters/postgres_dependencies.py` integrates them without changing old storage records.
- `domains/procurement/reviewed_source_queries.py`: frozen `ReviewedSkuRow` and `ReviewedSourceSkuQuery`; shared SKU-source validation stays in `source_queries.py`.
- `application/reviewed_bom_queries.py`: authorized selection/read/execute/register flow and immutable `ReviewedQueryExecution` payload.
- `interfaces/reviewed_bom_query.py`, `interfaces/correction_impact.py`, `bootstrap.py`: strict public caller, explicit capability init and composition.
- Tests in `tests/unit/test_correction_dependencies.py`, `tests/contract/test_reviewed_dependency_store.py`, `tests/unit/test_reviewed_source_queries.py`, `tests/contract/test_reviewed_bom_query.py`, `tests/integration/test_reviewed_bom_query_cli.py`; package probe in `tools/reviewed_query_package_probe.py`.

### Task 1: Typed correction roots and old-wire compatibility

**Consumes:** existing `ArchivedClaimRef`, `DependencyManifest`, `DependencySnapshot`, `SemanticCodec`.
**Produces:** `ApprovedCorrectionRef(source: ArchivedClaimRef, task_id: str, task_digest: str, decision_id: str, correction_id: str)`; property `reference_id -> str` returns correction_id and `snapshot_id -> str` returns source.snapshot_id. `ArchivedClaimRef.reference_id` returns its existing assertion_id without adding serialized fields. `DependencyRoot = ArchivedClaimRef | ApprovedCorrectionRef`.

- [x] After plan approval, create a feature implementation Issue under #41 referencing decision #222, the approved spec/plan and this acceptance contract. Use architecture-plan-sync/manage-github-planning and an isolated execution ledger. The decision and feature remain open until their acceptance is merged.
- [x] Before changing codec/records, capture `bootstrap.archive_codec().dumps(DependencySnapshot(manifest(claim('a','source')), 'recorder', AT))` using `tests.unit.test_dependencies` fixtures into `tests/fixtures/dependency-archive-only-v1.json`; record baseline revision and SHA256 in test comments.
- [x] Write RED tests `test_correction_is_data_root`, `test_root_variants_require_exact_types`, `test_missing_original_root_rejected`, `test_cross_variant_id_collision_rejected`, `test_old_snapshot_wire_is_identical`. Assert source+correction -> reviewed row -> query traversal, bounded frontier, unchanged declared/global coverage and exact old JSON/digest/snapshot identity.
- [x] Run `uv run pytest -q tests/unit/test_correction_dependencies.py`; observe missing new record/API failures.
- [x] Implement exact typed/bounded IDs and SHA256 digest validation. Require a correction's source ArchivedClaimRef among manifest roots. Canonically order and deduplicate all roots by reference_id; validate known-input membership and impact using that ID. Preserve old serialized fields, limits, policy and graph rules. Register only the new neutral record in `bootstrap.archive_codec()`.
- [x] Run new unit tests plus `tests/unit/test_dependencies.py`; all pass and old fixture is byte-identical. Commit the coherent root/codec/test change.

### Task 2: Explicit correction-root storage capability

**Consumes:** Task1 roots; existing `DocumentReviewJournal.get(scope,task_id,as_of) -> ReviewHistory` and `AssertionArchive`.
**Produces:** optional injected journal on `PostgresDependencyStore`; concrete `initialize_corrections() -> None`. Existing `DependencyStore.append/get` signatures remain unchanged.

- [x] Write RED real-Postgres tests `test_capability_is_explicit_and_old_rows_unchanged`, `test_missing_capability_and_reader_fail_closed`, `test_correction_roots_retry_restart_and_atomic_rollback`, `test_root_requires_exact_approved_journal_binding`, `test_retained_root_corruption_is_integrity_failure`.
- [x] Run new contract file with a task-owned disposable Postgres DSN; observe missing API/capability failures.
- [x] Keep archive1/review1/dependency1 meta and existing tables untouched. Explicitly create `pil_dependency_correction_meta(singleton,version)` with version1 and `pil_dependency_correction_roots(scope,dependency_snapshot_id,correction_id,source_snapshot_id,assertion_id,task_id,task_digest,decision_id)`. Add immutable guards and foreign keys to dependency snapshot, archive membership, task and decision. Acquire the existing dependency advisory init lock; require initialized archive1/review1/dependency1; make exact capability initialization idempotent. Ordinary reads/appends never initialize it.
- [x] Split source and correction membership rows. Resolve every correction root through the injected journal, checking exact task digest, decision/correction IDs, APPROVE, scope/source/previous assertion and approval no later than registration. Preserve immutable source checks. Missing capability/reader is DependencyUnavailableError; unsupported/corrupt capability or retained evidence is DependencyIntegrityError; new missing evidence is DependencyNotFoundError; invalid new selection is DependencyContractError. Translate review infrastructure errors into dependency envelopes without raw backend text.
- [x] Read back and compare exact archived and correction membership sets, payload/hash/command identities and journal evidence. Check unexpected correction membership for old records when capability exists. Use the existing append transaction/lock so a mid-write failure leaves neither snapshot nor partial memberships.
- [x] Run new contracts plus `tests/contract/test_dependency_store.py` and `tests/contract/test_document_review_journal.py`. Assert concurrent exact commands converge, changed actor/selection conflicts, SQL immutable guards hold and archive-only reads/appends still work without review tables. Commit.

### Task 3: Actual reviewed-row and set-query producers

**Consumes:** exact DocumentSnapshot and canonical tuple[ReviewHistory,...], approved as-of and ProvenanceContext; Task1 root graph.
**Produces:** frozen `ReviewedSkuRow(source:SourceAssertion, review:ReviewHistory, as_of:datetime, provenance:DecisionProvenance)` and `ReviewedSourceSkuQuery(snapshot:DocumentSnapshot, reviews:tuple[ReviewHistory,...], as_of:datetime, provenance:DecisionProvenance)`. Query properties: `rows`, `value`, `known_skus`, `status`, `missing_reference_ids`, `reference_id`, `event`, `execution_digest`; row properties: `reference_id`, `value`, `event`. `reviewed_dependency_manifest(query,request_id) -> DependencyManifest` includes every source SKU root and selected correction root. Factories `reviewed_query_provenance(context)` and `reviewed_row_provenance(context)` return fixed typed DecisionProvenance.

- [x] Write RED unit tests for duplicate GPU-A rows with one changed to GPU-B (`assert result.value == ('GPU-A','GPU-B')`), missing->known and known->null (`assert result.value is None`), unselected unknown, equal-value approval (`assert reviewed.reference_id != original.reference_id`), case/numeric strings, selection-order invariance, duplicate task/conflicting selected assertion, pending/rejected/foreign/non-SKU/future review, exact metadata types, and32/33 row budgets. Assert actual row events consume source+correction and final event consumes original/reviewed row refs, never more than32.
- [x] Run `uv run pytest -q tests/unit/test_reviewed_source_queries.py`; observe missing producer failures.
- [x] Extract `validated_sku_inputs(snapshot) -> tuple[SourceAssertion,...]` from original source validation with no legacy output/identity change. Keep original workflow validation fixed. Add reviewed workflow `reviewed-source-sku-query`, row component `procurement-reviewed-sku-row`, query component `procurement-reviewed-source-sku-set`, implementation1 and approved policy. Enforce fixed metadata/null irrelevant fields and exact types on new frozen records.
- [x] Execute one row producer per selected original assertion; preserve source order in the final input view, canonicalize graph/event IDs. Derive reviewed value from exact proposed values without altering source objects. Complete reviewed results use EpistemicStatus.INFERRED with the explicit selected-review basis; incomplete results use UNRESOLVED/null. Never claim the new value was observed in the source or is canonical. Bind source, exact review selection/content, as-of encoding, full execution metadata and result to identities. Include original/assertion evidence and review decision evidence separately.
- [x] Run new unit tests plus original `tests/unit/test_source_sku_query.py` and `tests/unit/test_bom.py`. Verify64 roots/33 references at32 corrected rows, each data event within its bound. Commit.

### Task 4: Authorized application, explicit caller and capability init

**Consumes:** ArchiveReader, DocumentReviewService, DependencyStore, actual reviewed producer and server clock.
**Produces:** `ReviewedBomQueryService.execute(scope,snapshot_id,request_id,task_ids:tuple[str,...],as_of,execution,*,context) -> ReviewedQueryExecution`; `ReviewedQueryExecution.as_dict()` returns reviewed_query/selected_reviews/dependency_snapshot and explicit selection/completeness/no-governing flags. `bootstrap.build_reviewed_bom_query_service(dsn,*,clock=None)` composes these ports.

- [x] Write RED Postgres/application and subprocess tests: exact source deletion -> original query -> approve -> explicit reviewed result -> retry/restart; unchanged original query/bytes; denied scope/permission and malformed identities fail before I/O; recording sampled after computation; substituted producer source/selection/as-of/context rejected; changed as-of/actor/context/request conflicts; uninitialized capability fails without writes.
- [x] Run new contract/CLI files; observe missing service/module/command failures.
- [x] Authorize REVIEW+READ_EVIDENCE first; preflight exact IDs/tuple cardinality/context/clock/as-of <= execution before reads. Load the exact archive, resolve only selected tasks at as-of through DocumentReviewService, execute the typed producer and compare exact requested source/selection/as-of/execution digest before append. Stamp recording after production. Bind returned execution to its exact manifest. Preserve the first receipt/time on retry.
- [x] Add `correction_impact init-reviewed`, calling only initialize_corrections and returning explicit capability name/version. Existing init still returns dependency schema1 and never creates the capability. Inject the lazy neutral journal in dependency-store composition without requiring review schema for old archive-only operations.
- [x] Implement `interfaces.reviewed_bom_query` with the approved argv. Reviews JSON has exactly task_ids, strict UTF-8/duplicate-key/depth/32768-byte checks; context has exactly run_id/code_revision/started_at and the same bounds. Canonically sort valid unique selections and bind selection+as-of to config/command identity. Use trusted human env/config conventions; sanitized JSON exit2/no stdout on every typed or argument failure. Reuse existing SourceQueryContractError and dependency/review/scope envelopes; do not add a vocabulary code without a demonstrated need.
- [x] Run new contract/subprocess tests plus original query/impact CLI tests. Verify output says explicit_selected_set/unselected_reviews:not_evaluated, recomputation_executed:true for this caller, governing_state_updated:false, original_source_updated:false, no global-freshness claim. Generic impact stays conservative. Commit.

### Task 5: Installed artifact, evidence and delivery

**Consumes:** all prior task interfaces; approved spec, Issue #222, semantic evidence schema and existing delivery harness.
**Produces:** qualified source/installed caller, latest-revision semantic evidence, synchronized documentation and precise Issue closeout.

- [ ] Add a RED installed-caller probe `tools/reviewed_query_package_probe.py`, invoked by `tools/package_smoke.py` using its existing storage test DSN and clean wheel environment. Assert archive-only works before capability, reviewed replay fails typed until explicit init, source deletion/export equality, actual original query -> exact SKU approval -> reviewed value change/new reference, duplicate-row specificity, original query unchanged and retry equal. Base install without storage must fail typed, never import psycopg unguarded.
- [ ] Implement probe integration; run `make package-smoke` with dedicated disposable Postgres. Document the exact capability init, CLI, provenance, selected view and residual boundaries in `docs/domains/procurement/reviewed-source-sku-query.md`, README, milestone map and handoff. Mark this plan's task outcomes in its isolated ledger.
- [ ] Seal source, run exact-head `make check`/coverage ratchet, `make package-smoke`, all existing30 public challenges/known-bad mutations and focused tests. This is a new capability, not by itself a shipped defect or model swap; add a challenge if a shipped semantic defect is actually found.
- [ ] Apply architecture-review/review-semantic-change with one fresh-context whole-branch reviewer; fix material findings RED/GREEN and rerun invalidated qualification. Record every seven-family disposition, exact commands/revision and review result in the canonical semantic evidence JSON embedded in the PR. No completion with stale/pending receipts.
- [ ] Publish a feature PR with primary M2 and Part of #13/#35/#37/#41; close the feature Issue only when its implementation acceptance is complete, and close #222 only when the approved decision/spec/plan are merged. All required deterministic PR checks and final body-bound contract must pass; resolve/rebut arriving actionable review threads before merge.
- [ ] After authorized merge, compare main's tree to qualified head, run the actual reviewed CLI/storage probe pinned to merged main, audit/reconcile planning, retain advisory audit success/failure separately, and remove only task-owned test resources. Do not infer deployment, canonical state or complete M2/M4/M5 acceptance.

## Plan self-review and execution handoff

The five Review Focus cases map to explicit tests. All interfaces are defined above; each spec
section maps to Tasks1..5. The additive capability avoids mutating schema1's immutable meta and
preserves old wire shape. The intermediate row producers meet the spec's data-input budget.
Remaining implementation choices are private mechanics, not new correction-selection policy.

Recommended execution is native/inline with one independent final reviewer: tasks share root,
codec and receipt contracts, so separate implementer contexts would repeatedly reload the same
boundaries. Execution is native/inline under the maintainer's approved; proceed authorization. The plan's self-review is complete; one fresh independent review gates final delivery.
