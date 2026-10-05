# Demo Storytelling and Evidence Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the reviewer visibly connect each finding to its supporting documents, then introduce the live workflow with an editable explanatory deck and a concise, narrated-by-banner browser recording.

**Architecture:** Keep procurement facts, evidence identities, source APIs, digests, and approval semantics unchanged. Improve only the shipped review presentation contract, build the native deck from repository-authoritative architecture material, and use a reproducible Playwright recording harness to show rendered slides before the authenticated live reviewer.

**Tech Stack:** Python 3.12, packaged HTML/JavaScript/CSS, pytest, Node page probes, Playwright Chromium, native presentation connector, PDF/PNG slide rendering, WebM/VP8, JSON evidence artifacts.

**Spec:** `docs/superpowers/specs/2026-10-05-demo-storytelling-evidence-focus-design.md`

## Global Constraints

- Primary M9 / Issue #74; part of M5 and #72; stack on PR #193 without merge, deployment, corpus expansion, or Issue closure.
- Procurement remains the only implemented vertical; every other domain is labeled as a potential application.
- Models may interpret requests but cannot supply quantities, evidence authority, review permission, or save authority.
- Only run-bound references already present in `facts.evidence` may be shown as supporting documents.
- Internal `ReviewBrief`, digest, receipt, persistence, and conflict contracts remain unchanged; only user-facing “exact brief” wording changes.
- The private reviewer token must never appear in publishable frames, URLs, storage, logs, reports, or repository artifacts.
- The final recording uses a 1440×900 safe-area canvas, paced character-by-character input, short reading pauses, italic Who/What/Why/How/When banners, and truthful local/synthetic/unmerged/undeployed labels.
- Report the browser interaction clock separately from final media-container duration; do not call automated pacing human rehearsal timing.
- Diagnose PR #193's existing coverage failure separately; do not conceal or overwrite it.

## Review Focus

- A finding with no evidence renders an explicit unsupported state and performs no automatic source request; pin this in Task 1.
- Authority evidence has no worksheet cells but must still receive readable selected-document treatment; pin this in Tasks 1 and 2.
- A failed automatic or manual source load must preserve the finding and selected document while exposing only the safe page error; pin this in Task 2.
- Lock, replacement, recovery, or a stale callback must not leave an old document visually selected for a different run; pin this in Task 2.
- Video automation must type visible scenario fields gradually while keeping authentication and all secret-bearing diagnostics out of the media and report; pin this in Task 4.

---

### Task 1: Evidence-Focused Reviewer Presentation

**Files:**
- Modify: `src/procurement_intelligence_lab/interfaces/review_page.py`
- Modify: `tests/unit/review_page_probe.cjs`
- Modify: `tests/unit/live_review_page_probe.cjs`
- Modify: `tests/unit/review_page_recovery_probe.cjs`
- Modify: `tests/unit/test_review_page.py`
- Modify: `tests/unit/test_live_review_page.py`
- Modify: `tests/unit/test_review_page_recovery.py`

**Interfaces:**
- Consumes: existing `facts.evidence` entries and `/api/source` payloads with `cells`, `headers`, `highlighted_columns`, `authority`, and `evidence`.
- Produces: `renderEvidence(view, facts)`, `selectEvidence(button, ref, view, version)`, and `renderSource(source)` page functions; accessible evidence cards with `aria-pressed`; unchanged HTTP payloads.

- [ ] **Step 1: Add failing Node page-probe assertions**

Assert that rendered copy says “Review finding”, “Approve this finding”, “Reject this finding”, and “Verified version”; evidence references render as document cards; the first reference is requested automatically; the selected card exposes `aria-pressed="true"`; worksheet payloads show “Highlighted cells support this finding”; authority payloads show “Governing authority record”; empty evidence shows an explicit unsupported message and sends no source request.

- [ ] **Step 2: Run the focused unit tests and verify RED**

Run: `uv run --extra workflow pytest -q tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_review_page_recovery.py`

Expected: failures for the new copy, automatic source request, selected-card state, and readable source treatments.

- [ ] **Step 3: Implement the minimal page presentation change**

In `review_page.py`, add the evidence workspace markup and CSS, split evidence-card rendering from source rendering, automatically invoke the first card only after a fully validated current view, and preserve `epoch`, `busy`, current-run, safe-error, and stale-callback guards. Keep complete authority JSON under a disclosure after the readable authority summary. Clear selection and source content in `clear()` and before rendering a replacement view.

- [ ] **Step 4: Run focused unit tests and verify GREEN**

Run: `uv run --extra workflow pytest -q tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_review_page_recovery.py`

Expected: all selected tests pass with zero unhandled JavaScript errors.

- [ ] **Step 5: Commit the reviewer presentation**

```bash
git add src/procurement_intelligence_lab/interfaces/review_page.py tests/unit/review_page_probe.cjs tests/unit/live_review_page_probe.cjs tests/unit/review_page_recovery_probe.cjs tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_review_page_recovery.py
git commit -m "feat: focus reviewer on supporting evidence"
```

### Task 2: Real Browser Evidence and Recovery Acceptance

**Files:**
- Modify: `tests/integration/test_review_web.py`
- Modify: `tests/integration/test_browser_review.py`
- Modify: `tests/integration/test_browser_recovery.py`
- Modify: `tests/integration/test_original_showcase_live.py`

**Interfaces:**
- Consumes: Task 1's user-facing copy and accessible evidence-card contract.
- Produces: installed-browser acceptance for automatic selection, exact source linkage, highlighted worksheet cells, authority presentation, safe failure, recovery, and idempotent approval.

- [ ] **Step 1: Update public HTML and browser tests before production repair**

Replace old visible labels in assertions and add tests that: the first evidence request occurs automatically; its card stays selected; a manual second selection changes exactly one selected card; cell highlights match `highlighted_columns`; authority evidence has readable authority treatment; failed source loading preserves the current finding and selection; lock/replacement/recovery removes stale source state.

- [ ] **Step 2: Run the affected integration tests and verify failures expose incomplete Task 1 behavior**

Run: `uv run --extra workflow pytest -q tests/integration/test_review_web.py tests/integration/test_browser_recovery.py`

Expected: any missing public-boundary behavior fails before test expectation repair is considered complete.

- [ ] **Step 3: Repair selectors and page behavior narrowly**

Change only presentation selectors/callback sequencing needed by the public tests. Do not change `/api/source`, evidence payloads, review receipts, or save semantics.

- [ ] **Step 4: Run actual installed Chromium acceptance**

Run the clean installed fixture walkthrough and browser-recovery suite with the repository's existing `PIL_BROWSER_PYTHON` and cached Chromium conventions. Then run the original-source installed-browser case when its existing local Qwen/runtime prerequisites are available.

Expected: exact source IDs, cells, selected cards, authority records, recovery, review, and single-save assertions pass; credential storage remains empty.

- [ ] **Step 5: Commit public-boundary acceptance**

```bash
git add tests/integration/test_review_web.py tests/integration/test_browser_review.py tests/integration/test_browser_recovery.py tests/integration/test_original_showcase_live.py
git commit -m "test: verify evidence-focused browser review"
```

### Task 3: Native Explanatory Deck

**Files:**
- Create: `docs/project/demo-storytelling-deck.md`
- Create: `docs/assets/rehearsal-v2/slides/slide-01.png` through `slide-08.png`
- Create: `docs/assets/rehearsal-v2/slides/contact-sheet.png`
- Local evidence: `artifacts/demo-storytelling/v1/presentation.pdf`, raw presentation readback, issue-check output, and render metadata

**Interfaces:**
- Consumes: `docs/architecture.md`, `docs/architecture/platform-semantics.md`, `docs/architecture/universal-stage-semantics.md`, `docs/architecture/domain-verticals.md`, `docs/product/use-cases.md`, `docs/product/showcase-discrepancy-contract.md`, and the approved spec's eight-slide narrative.
- Produces: one editable native presentation, one canonical presentation URL/ID, eight ordered 16:9 slide renders, and a repository manifest that records claims, sources, order, and truthful capability boundaries.

- [ ] **Step 1: Create the native presentation in the connected presentation workspace**

Use the net-new presentation authoring route required by the Google Slides skill. Build the approved eight-slide sequence with native text and diagrams. Use navy structure, amber unresolved/conflict, and green only for positive supported outcomes. Add compact repository-source notes and explicit “potential application—not implemented” labels on the verticals slide.

- [ ] **Step 2: Perform structural readback and local issue checking**

Read the completed native deck once, save the unmodified response under the local evidence directory, and run the presentation output issue checker. Repair all errors and inspect warnings for empty/typed bullets, undersized narrative text, placeholders, or blank slides.

- [ ] **Step 3: Export and render the deck once for visual QA**

Export to PDF and render all eight slides at 120 DPI. Build a contact sheet, inspect every slide, and collect clipping, overflow, contrast, arrow ambiguity, unsupported-claim, and unused-space defects before one consolidated repair pass. Re-render after any structural repair.

- [ ] **Step 4: Record the presentation manifest**

Write `docs/project/demo-storytelling-deck.md` with slide order, native deck link, repository claim sources, visual QA disposition, and non-claims. Copy the final ordered slide PNGs and contact sheet into `docs/assets/rehearsal-v2/slides/` for reproducible video input.

- [ ] **Step 5: Commit deck evidence and rendered inputs**

```bash
git add docs/project/demo-storytelling-deck.md docs/assets/rehearsal-v2/slides
git commit -m "docs: add procurement demo story deck"
```

### Task 4: Reproducible Deck-to-Live-Demo Recording

**Files:**
- Create: `tools/record_demo_story.py`
- Create: `tests/unit/test_record_demo_story.py`
- Create: `docs/assets/rehearsal-v2/index.html`
- Create: `docs/assets/rehearsal-v2/walkthrough.vtt`
- Create: `docs/assets/rehearsal-v2/walkthrough.webm`
- Create: `docs/project/demo-storytelling-results.json`
- Local evidence: `artifacts/demo-storytelling/v1/recording/`

**Interfaces:**
- Consumes: Task 3's ordered slide PNGs, a loopback reviewer origin, a token-file path, and Task 1's accessible labels/cards.
- Produces: `RecordingConfig` with origin/token/slides/output/typing-delay/read-pause values; a WebM recording; a credential-free compact JSON report; a browser-playable captioned wrapper.

- [ ] **Step 1: Write failing recording-helper tests**

Test deterministic slide ordering, safe-area dimensions, banner schema requiring nonempty Who/What/Why/How/When, character-by-character typing events rather than atomic fill for visible fields, token redaction from serialized configuration/report, and refusal to overwrite an existing evidence directory.

- [ ] **Step 2: Run helper tests and verify RED**

Run: `uv run --extra workflow pytest -q tests/unit/test_record_demo_story.py`

Expected: import or contract failures because the recording helper does not exist.

- [ ] **Step 3: Implement the minimal recording harness**

Implement `RecordingConfig`, pure banner/slide/input-step builders, report redaction checks, and a Playwright entry point. Show slides full-frame in order, authenticate outside publishable frames, inject a fixed italic bottom banner into the reviewer, type question and cutoff values with Playwright keyboard delay while the caret is visible, visibly submit, and show automatic source selection/highlighting. Use short bounded pauses and one deep conflict scenario. Close context/browser cleanly so video buffers flush.

- [ ] **Step 4: Run unit tests and a zero-inference dry recording**

Run the helper tests, then record against a fixture reviewer with disposable output. Verify no token occurrence in WebM-adjacent text files, report, URL, cookies, local storage, or session storage.

- [ ] **Step 5: Record the authorized live demonstration once**

Use the prepared loopback reviewer and private token file without printing either secret. Retain exact run/source/review/save assertions. Do not retry model inference automatically; if a publishable recording fails, retain it separately and require a fresh output directory.

- [ ] **Step 6: Validate media and browser playback**

Verify WebM is VP8, seekable, 1440×900, includes all eight slides followed by the live section, contains visible paced typing, shows changing italic five-question banners, and does not crop top or bottom content. Record interaction time, container duration, SHA-256, scenario outcome, source count, selection/highlight assertions, and credential checks separately in `demo-storytelling-results.json`.

- [ ] **Step 7: Commit the recording harness and final media**

```bash
git add tools/record_demo_story.py tests/unit/test_record_demo_story.py docs/assets/rehearsal-v2 docs/project/demo-storytelling-results.json
git commit -m "feat: record explanatory procurement demo"
```

### Task 5: Durable Evidence, Full Verification, and Latest-Revision Review

**Files:**
- Modify: `docs/product/local-browser-review-v1.md`
- Modify: `docs/project/demo-rehearsal.md`
- Modify: `docs/project/handoff.md`
- Modify: `docs/development/milestone-map.md`
- Create: `docs/project/demo-storytelling-evidence.json`
- Modify: PR #193 body after final committed revision

**Interfaces:**
- Consumes: Tasks 1–4 final revision, native deck metadata, installed browser results, and media verification.
- Produces: schema-valid semantic-change evidence, synchronized handoff/milestone status, and a PR body describing the exact latest revision and remaining gates.

- [ ] **Step 1: Write the seven-family evidence artifact as `not_ready` during verification**

Record authoritative inputs/output, unchanged scope/as-of and governing policy, retained evidence, typed failures, and all seven required scenario dispositions. Include exact commands and distinguish deck/video evidence from procurement/model-quality evidence.

- [ ] **Step 2: Run focused and repository-wide verification**

Run:

```bash
uv run --extra workflow pytest -q tests/unit/test_review_page.py tests/unit/test_live_review_page.py tests/unit/test_review_page_recovery.py tests/unit/test_record_demo_story.py tests/integration/test_review_web.py tests/integration/test_browser_recovery.py
make package-smoke
make challenges
make check
```

Also run the installed browser caller from Task 2 and the media checks from Task 4. Preserve exact argv, exit status, and artifact paths. Diagnose the existing PR #193 coverage failure independently before interpreting the new full-check result.

- [ ] **Step 3: Validate semantic evidence and synchronize durable documentation**

Run `uv run --extra workflow python tools/validate_semantic_change.py --evidence docs/project/demo-storytelling-evidence.json` with the repository's required routing/skills arguments. Update the product contract, rehearsal guide, handoff, and M9 milestone entry without claiming merge, deployment, human timing, second-vertical implementation, or broader quality.

- [ ] **Step 4: Commit documentation and evidence**

```bash
git add docs/product/local-browser-review-v1.md docs/project/demo-rehearsal.md docs/project/handoff.md docs/development/milestone-map.md docs/project/demo-storytelling-evidence.json
git commit -m "docs: record evidence-focused demo acceptance"
```

- [ ] **Step 5: Review the latest revision fresh**

Use `.agents/skills/review-semantic-change/SKILL.md` against the final committed revision. Inspect public copy, evidence/source identity, callback/lock/recovery behavior, deck claims, credential boundaries, media integrity, and exact command evidence. Resolve every actionable finding and rerun invalidated checks.

- [ ] **Step 6: Finalize the evidence revision and PR body**

Set evidence `revision`, review revision, findings, unresolved findings, and completion truthfully; revalidate and commit any final evidence-only update. Update PR #193 to identify M9/#74, `Part of` linked Issues, exact tests, deck/video artifacts, remaining gates, and the embedded semantic evidence JSON. Do not mark ready if required CI, local verification, or review is unresolved.

