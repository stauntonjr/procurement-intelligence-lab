# Procurement Reconciliation Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an authenticated procurement analyst resolve an exact item/project/site requirement conflict prospectively, with a required rationale and retained source evidence, through an analyst-first browser workflow.

**Architecture:** Add a procurement-owned human reconciliation decision, a repository port and SQLite adapter, and an application service that validates an exact active assessment before recording a prospective override. The corpus investigation service consumes the latest applicable override when projecting current state; the HTTP/browser layer exposes closed, explicit resolution choices and keeps technical history secondary.

**Tech Stack:** Python 3.12+, stdlib dataclasses and SQLite, repository Protocol ports, existing loopback HTTP server, packaged vanilla HTML/JavaScript, pytest, Playwright/Chromium workflow tests.

**Spec:** `docs/superpowers/specs/2026-10-05-procurement-reconciliation-review-design.md`

## Global Constraints

- Scope is exactly tenant + project + site + item; never document-wide.
- Effective time is server-generated at save time; no caller-supplied or retroactive time.
- Selecting a revision requires a non-empty bounded rationale and an eligible displayed claim ID.
- Both winning and losing assertions and all evidence remain retained.
- Historical state and decisions remain unchanged; only later as-of evaluations may consume the override.
- Models cannot select a governing revision or supply identity, scope, authority, or effective time.
- No resolution triggers a purchase, message, alert, or external action.
- Domain types remain framework-independent; SQLite and HTTP mechanics remain adapters/interfaces.

## Review Focus

- A stale brief or changed candidate set must fail without persisting a reconciliation decision.
- An override for one item/project/site must not affect another scope sharing the same revision ID.
- A query before `effective_at` must retain the original unresolved result; a later query may use the override.
- Three or more conflicting candidates must remain unresolved and expose no misleading A/B control.
- Replaying the same exact resolution must return one identity; changing choice or rationale must conflict.

---

### Task 1: Ratify the prospective human-reconciliation contract

**Files:**
- Create: `docs/adr/034-prospective-human-reconciliation.md`
- Modify: `docs/product/local-browser-review-v1.md`
- Modify: `docs/product/local-qwen-review-v1.md`
- Test: `tests/unit/test_documentation.py`

**Interfaces:**
- Consumes: approved design specification.
- Produces: ADR-034 terminology and the public `/api/reconcile` contract used by later tasks.

- [ ] **Step 1: Write the failing documentation assertions**

Assert ADR-034 exists and names exact item/project/site scope, server-owned `effective_at`, required rationale, retained losing assertions, and the prohibition on retroactive changes and external actions.

- [ ] **Step 2: Run the documentation test and observe failure**

Run: `uv run pytest -q tests/unit/test_documentation.py -k reconciliation`
Expected: FAIL because ADR-034 and the new public contract are absent.

- [ ] **Step 3: Add ADR-034 and update both reviewer contracts**

Specify `POST /api/reconcile` fields exactly as `run_id`, `brief_id`, `digest`, `outcome`, `selected_claim_id`, and `rationale`; define `selected_claim_id` as empty only for non-selection outcomes. Record that the first shipped resolver supports exactly two eligible conflicting required-quantity claims.

- [ ] **Step 4: Run the documentation test**

Run: `uv run pytest -q tests/unit/test_documentation.py -k reconciliation`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add docs/adr/034-prospective-human-reconciliation.md docs/product/local-browser-review-v1.md docs/product/local-qwen-review-v1.md tests/unit/test_documentation.py && git commit -m "docs: ratify prospective reconciliation review"`

### Task 2: Add the procurement reconciliation-decision model

**Files:**
- Create: `src/procurement_intelligence_lab/domains/procurement/review_reconciliation.py`
- Modify: `src/procurement_intelligence_lab/domains/procurement/__init__.py`
- Test: `tests/unit/test_review_reconciliation.py`

**Interfaces:**
- Consumes: `StateScope`, `EvidenceRef`, and claim IDs from `GoverningClaim`.
- Produces: `ReconciliationReviewOutcome`, `HumanReconciliationDecision`, and `prospective_decision_id`.

- [ ] **Step 1: Write failing domain tests**

Cover `select_governing_revision`, `keep_unresolved`, `confirm_assessment`, and `assessment_needs_correction`; assert selection requires a candidate claim and rationale, unresolved requires rationale, non-selection rejects a selected claim, all datetimes are aware, candidate IDs are unique, selected ID is a candidate, evidence is non-empty and unique, and exact scope participates in stable identity.

- [ ] **Step 2: Run the domain tests and observe import failure**

Run: `uv run pytest -q tests/unit/test_review_reconciliation.py`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement immutable domain records**

Create `ReconciliationReviewOutcome(StrEnum)` and frozen `HumanReconciliationDecision` with exact fields: `decision_id`, `brief_id`, `brief_digest`, `subject_key`, `scope`, `outcome`, `candidate_claim_ids`, `selected_claim_id`, `rationale`, `reviewer_id`, `policy_id`, `recorded_at`, `effective_at`, and `evidence`. Enforce `recorded_at == effective_at` for this version and derive identity from every semantic field except the supplied `decision_id`, which must equal the derived value.

- [ ] **Step 4: Run the domain tests**

Run: `uv run pytest -q tests/unit/test_review_reconciliation.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/domains/procurement/review_reconciliation.py src/procurement_intelligence_lab/domains/procurement/__init__.py tests/unit/test_review_reconciliation.py && git commit -m "feat: define scoped reconciliation decisions"`

### Task 3: Persist and query prospective decisions behind a port

**Files:**
- Create: `src/procurement_intelligence_lab/ports/reconciliation_reviews.py`
- Create: `src/procurement_intelligence_lab/adapters/sqlite_reconciliation_reviews.py`
- Test: `tests/contract/test_reconciliation_review_store.py`

**Interfaces:**
- Consumes: `HumanReconciliationDecision`, `RequestContext`, exact brief identity, candidate IDs.
- Produces: `ReconciliationReviewStore.record(decision, *, context)`, `.latest(subject_key, as_of, *, context)`, and `.for_brief(brief_id, *, context)`.

- [ ] **Step 1: Write failing store-contract tests**

Assert owner/scope isolation, latest decision only when `effective_at <= as_of`, pre-effective queries returning `None`, exact replay identity, changed outcome/selection/rationale conflicts, duplicate/corrupt rows fail closed, and one item's override cannot leak to another item or site.

- [ ] **Step 2: Run the store tests and observe failure**

Run: `uv run pytest -q tests/contract/test_reconciliation_review_store.py`
Expected: FAIL because the port and adapter are absent.

- [ ] **Step 3: Implement the Protocol and SQLite adapter**

Use a dedicated `reconciliation_reviews` table keyed by `decision_id`, with a unique exact-request replay key over brief/digest/outcome/selection/rationale/reviewer. Store explicit tenant/project/site/item/effective columns plus canonical payload; validate relational columns against decoded payload on every read. Use `BEGIN IMMEDIATE` for record.

- [ ] **Step 4: Run the store tests**

Run: `uv run pytest -q tests/contract/test_reconciliation_review_store.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/ports/reconciliation_reviews.py src/procurement_intelligence_lab/adapters/sqlite_reconciliation_reviews.py tests/contract/test_reconciliation_review_store.py && git commit -m "feat: persist prospective reconciliation decisions"`

### Task 4: Apply overrides to governed state without rewriting history

**Files:**
- Modify: `src/procurement_intelligence_lab/application/corpus_investigation.py`
- Modify: `src/procurement_intelligence_lab/domains/procurement/state.py`
- Test: `tests/unit/test_reconciliation.py`
- Test: `tests/unit/test_corpus_investigation.py`

**Interfaces:**
- Consumes: `ReconciliationReviewStore.latest(subject_key, as_of, context)` and the complete `GoverningClaimDecision` candidate set.
- Produces: `project_governed_required_quantity(..., human_decision: HumanReconciliationDecision | None = None)` and facts containing `governance_candidates`.

- [ ] **Step 1: Add failing temporal and scope tests**

Prove unresolved before `effective_at`, selected claim governs at/after `effective_at`, losing claims remain on the decision, another item/site remains unchanged, future/ineligible/foreign claim IDs fail, equal-value shared governance still uses policy, and three-candidate conflict ignores the A/B resolver path.

- [ ] **Step 2: Run the focused tests and observe failure**

Run: `uv run pytest -q tests/unit/test_reconciliation.py tests/unit/test_corpus_investigation.py`
Expected: FAIL on missing override support and candidate DTOs.

- [ ] **Step 3: Implement the override projection**

Add a narrow human-decision branch after ordinary eligibility filtering. It may select only an active eligible required-quantity claim for the same canonical key and scope. `keep_unresolved` returns unresolved with all candidates losing. Confirmation/correction do not alter policy output. Add candidate entries to brief facts with `claim_id`, `revision_id`, `value`, `unit`, `evidence_ids`, and eligibility/disposition; do not derive labels from array position outside the UI.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest -q tests/unit/test_reconciliation.py tests/unit/test_corpus_investigation.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/application/corpus_investigation.py src/procurement_intelligence_lab/domains/procurement/state.py tests/unit/test_reconciliation.py tests/unit/test_corpus_investigation.py && git commit -m "feat: project prospective reconciliation overrides"`

### Task 5: Validate and record exact reconciliation requests

**Files:**
- Create: `src/procurement_intelligence_lab/application/reconciliation_review.py`
- Modify: `src/procurement_intelligence_lab/interfaces/workflow.py`
- Modify: `src/procurement_intelligence_lab/interfaces/review_sources.py`
- Test: `tests/unit/test_reconciliation_review_service.py`

**Interfaces:**
- Consumes: exact `ReviewBrief`, parsed `governance_candidates`, `ReconciliationReviewStore`, investigator, server clock, `RequestContext`.
- Produces: `ReconciliationReviewService.reconcile(run_id, brief_id, digest, outcome, selected_claim_id, rationale, *, context) -> ReconciliationReviewResult` and `reconciliation_result_dto`.

- [ ] **Step 1: Write failing application tests**

Assert active brief/digest validation, exactly two eligible conflicting candidates for selection, required rationale, selected candidate membership, changed snapshot/facts rejection, server-owned aware time, exact scope, idempotent replay, stale newer decision conflict, no partial record on reinvestigation failure, and recomputed post-decision assessment.

- [ ] **Step 2: Run the service tests and observe failure**

Run: `uv run pytest -q tests/unit/test_reconciliation_review_service.py`
Expected: FAIL because the service is absent.

- [ ] **Step 3: Implement the service and composition wiring**

Re-read the exact active brief and fresh investigation before record; compare snapshot and canonical facts; construct the decision using one clock value; record it; reinvestigate at `effective_at`; return the durable decision plus recomputed facts. Extend `WorkflowComposition` with the reconciliation service and store without granting the LangGraph adapter implicit authority.

- [ ] **Step 4: Run service and existing workflow tests**

Run: `uv run pytest -q tests/unit/test_reconciliation_review_service.py tests/unit/test_review_workflows.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/application/reconciliation_review.py src/procurement_intelligence_lab/interfaces/workflow.py src/procurement_intelligence_lab/interfaces/review_sources.py tests/unit/test_reconciliation_review_service.py tests/unit/test_review_workflows.py && git commit -m "feat: add exact reconciliation review service"`

### Task 6: Expose the closed HTTP reconciliation boundary

**Files:**
- Modify: `src/procurement_intelligence_lab/interfaces/review_web.py`
- Modify: `src/procurement_intelligence_lab/interfaces/live_review.py`
- Test: `tests/integration/test_review_web.py`
- Test: `tests/integration/test_live_review.py`

**Interfaces:**
- Consumes: `ReconciliationReviewService.reconcile` from Task 5.
- Produces: authenticated `POST /api/reconcile` and an allowlisted response containing `decision` and `current_assessment`.

- [ ] **Step 1: Add failing real-HTTP tests**

Cover success for A, B, and unresolved; malformed/unknown outcome; absent or foreign claim; missing rationale; extra/caller effective-time field; stale digest; wrong auth/origin/scope; replay; application conflict 409; storage failure 503; and no mutation after every failed request.

- [ ] **Step 2: Run the HTTP tests and observe failure**

Run: `uv run pytest -q tests/integration/test_review_web.py tests/integration/test_live_review.py -k reconcile`
Expected: FAIL with route not found.

- [ ] **Step 3: Implement the route and typed mapping**

Require exactly six string fields. Keep body size, duplicate-field, Host, Origin, authentication, and no-cache guards unchanged. Translate semantic input errors to 422, scope denial to 403, missing run/brief to 404, stale/changed exact state to 409, and adapter failures to 503 without raw exception text.

- [ ] **Step 4: Run all reviewer HTTP tests**

Run: `uv run pytest -q tests/integration/test_review_web.py tests/integration/test_live_review.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/interfaces/review_web.py src/procurement_intelligence_lab/interfaces/live_review.py tests/integration/test_review_web.py tests/integration/test_live_review.py && git commit -m "feat: expose scoped reconciliation review"`

### Task 7: Replace the internal workflow UI with the analyst-first flow

**Files:**
- Modify: `src/procurement_intelligence_lab/interfaces/review_page.py`
- Modify: `tests/unit/test_review_page.py`
- Modify: `tests/unit/review_page_probe.cjs`
- Modify: `tests/unit/live_review_page_probe.cjs`
- Modify: `tests/unit/test_live_review_page.py`
- Test: `tests/integration/test_browser_review.py`

**Interfaces:**
- Consumes: `governance_candidates` and `/api/reconcile` from Tasks 4 and 6.
- Produces: analyst-first page copy and accessible resolution controls.

- [ ] **Step 1: Write failing page and browser assertions**

Require “Check procurement evidence”, “Item to review”/“Procurement question”, “Evidence available through”, and “Check for discrepancies”. Assert the page excludes “Independent interview reference demo”, “demo brief”, “Investigate and draft”, “Typed requests only”, “Recent owned runs”, “Selected persisted run”, “Review finding”, “Approve this finding”, and “Reject this finding” from primary visible content.

Assert assessment precedes evidence, evidence precedes resolution controls, technical history is collapsed, two eligible candidates render revision/value radio choices, rationale gates submission, the final button names the exact choice, and three candidates render only keep-unresolved/correction controls.

- [ ] **Step 2: Run page tests and observe failure**

Run: `uv run pytest -q tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/integration/test_browser_review.py`
Expected: FAIL on old copy/order and missing resolution controls.

- [ ] **Step 3: Implement the analyst-first page**

Render the plain-language assessment from typed facts. Move prior investigations, recovery, IDs, digest, JSON, and events into a closed `<details>` after resolution. Label prior records by item/time/status where data exists and keep raw run IDs inside details. Submit `/api/reconcile`, show the scoped prospective effect, preserve evidence selection on safe failure, and display the recomputed current assessment on success.

- [ ] **Step 4: Run page and browser tests**

Run: `uv run pytest -q tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_review_page_recovery.py tests/integration/test_browser_review.py tests/integration/test_browser_recovery.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/procurement_intelligence_lab/interfaces/review_page.py tests/unit/test_review_page.py tests/unit/review_page_probe.cjs tests/unit/live_review_page_probe.cjs tests/unit/test_live_review_page.py tests/integration/test_browser_review.py && git commit -m "feat: make reconciliation review analyst-first"`

### Task 8: Add the semantic regression oracle and durable evidence

**Files:**
- Create: `evals/agent_challenges/manifests/C028-scoped-prospective-reconciliation.json`
- Create: `evals/agent_challenges/fixtures/scoped_prospective_reconciliation/known_bad.py`
- Modify: `tests/unit/test_challenges.py`
- Modify: `docs/project/demo-storytelling-evidence.json`
- Modify: `docs/project/handoff.md`
- Modify: `docs/development/milestone-map.md`

**Interfaces:**
- Consumes: public HTTP and domain behavior from Tasks 2–7.
- Produces: a challenge that rejects retroactive/cross-scope or evidence-dropping implementations and latest-revision semantic evidence.

- [ ] **Step 1: Add the failing challenge manifest and known-bad case**

The oracle must reject an implementation that applies the override before `effective_at`, applies it to another item/site, or drops the losing assertion.

- [ ] **Step 2: Run the challenge and observe known-bad rejection/current-code failure until wired**

Run: `uv run python tools/run_agent_challenges.py --challenge C028`
Expected: current-code oracle fails before final wiring; known-bad is rejected.

- [ ] **Step 3: Complete durable evidence and planning updates**

Record authoritative inputs/output, scope/as-of rule, policy, evidence, typed failures, every scenario family, exact commands, review status, and current limits. Keep PR #193 and Issue #74 open; no deployment claim.

- [ ] **Step 4: Run challenge and evidence validation**

Run: `uv run python tools/run_agent_challenges.py --challenge C028 && uv run python tools/validate_semantic_change.py docs/project/demo-storytelling-evidence.json`
Expected: PASS with the known-bad implementation rejected.

- [ ] **Step 5: Commit**

Run: `git add evals/agent_challenges tests/unit/test_challenges.py docs/project/demo-storytelling-evidence.json docs/project/handoff.md docs/development/milestone-map.md && git commit -m "test: guard scoped prospective reconciliation"`

### Task 9: Verify the shipped caller and replace the demo recording

**Files:**
- Modify: `tools/record_demo_story.py`
- Modify: `tests/unit/test_record_demo_story.py`
- Modify: `docs/assets/rehearsal-v2/walkthrough.webm`
- Modify: `docs/project/demo-storytelling-results.json`
- Modify: `docs/project/demo-rehearsal.md`
- Modify: `docs/project/demo-storytelling-deck.md` only if slide wording must match implemented behavior.

**Interfaces:**
- Consumes: installed reviewer and public `/api/reconcile` behavior.
- Produces: a credential-free recording showing discrepancy, highlighted evidence, rationale, and one prospective scoped resolution.

- [ ] **Step 1: Add failing recorder acceptance assertions**

Require the report to identify selected revision, exact item/project/site scope, non-empty rationale, effective time after the original investigation cutoff, unchanged historical assessment, recomputed current assessment, retained evidence IDs, and no forbidden internal/demo copy in captured page text.

- [ ] **Step 2: Run recorder tests and observe failure**

Run: `uv run --extra workflow pytest -q tests/unit/test_record_demo_story.py`
Expected: FAIL because the recorder still exercises approve/reject.

- [ ] **Step 3: Update the recorder and capture through the installed public caller**

Use visible character typing, inspect both conflicting sources, select one revision, type the required rationale dynamically, save the prospective decision, and show the recomputed scoped status. Do not display credentials or imply retroactive effects, purchase authority, merge, or deployment.

- [ ] **Step 4: Run focused, integration, full, package, and challenge verification**

Run: `uv run --extra workflow pytest -q tests/unit/test_review_reconciliation.py tests/contract/test_reconciliation_review_store.py tests/unit/test_reconciliation_review_service.py tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_record_demo_story.py tests/integration/test_review_web.py tests/integration/test_live_review.py tests/integration/test_browser_review.py tests/integration/test_browser_recovery.py`

Run: `make integration`

Run: `make check`

Run: `make package-smoke`

Run: `make challenges`

Expected: every command exits 0; report exact counts and durations rather than estimating them.

- [ ] **Step 5: Perform latest-revision semantic and architecture review**

Use `.agents/skills/review-semantic-change/SKILL.md` and `.agents/skills/architecture-review/SKILL.md` against the actual head. Resolve every actionable finding and rerun invalidated checks. Validate the final evidence JSON against that revision.

- [ ] **Step 6: Commit and update PR #193**

Run: `git add tools/record_demo_story.py tests/unit/test_record_demo_story.py docs/assets/rehearsal-v2/walkthrough.webm docs/project && git commit -m "docs: record scoped reconciliation walkthrough"`

Push the branch, update the PR body with the exact semantic evidence and media hash, and report CI independently. Do not merge or deploy.
