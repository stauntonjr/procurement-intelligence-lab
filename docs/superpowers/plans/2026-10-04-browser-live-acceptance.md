# Real browser live-review acceptance

Owner-authorized continuation of approved corpus plan Task5C; execute inline using executing-plans.
Spec: ../specs/2026-10-03-procurement-demo-corpus-design.md. Primary#74; Partof#53/#67/#68/#72/#73.
Basea8d40ab (draftPR183), branchcodex/browser-live-acceptance. No merge or deployment.

## Goal and constraints

Exercise the actual reviewer page and installed server in cached local ARM64 Chromium using pinned
Playwright test tooling. Interactive browser connector is unavailable; cached Chromium151.0.7922.34
and Playwright1.63.0 are verified. No new model, prompt tuning, source policy, uploads or external
inference/traces. All model runs use the existing selected loopback Qwen. Distinguish fixture checks,
live demonstration repetitions and model-quality evaluation. Original tiny-fixture and fresh held-out
quality acceptance remain separate. Deployment and production authentication remain separate.

Disposable owned600-mode token file; enter token only into password control, never logs, URLs,
trace/HAR/video or screenshots while it is populated. Application context remains server-owned.
Actual UI submission/source/review/recovery gates cannot be replaced by helper context. Add only a
pinned development test dependency; installed product wheel remains minimal with optional workflow.

## Task 1: Real keyboard sign-in regression and test harness

Interfaces: existing shipped reviewer HTML/CLI; produces real-browser test setup consumed by Task2.

1. Add an opt-in real-browser integration fixture starting the clean installed CLI in a separate
process on OS-selected loopback port, with disposable private credentials. Test successful Enter
sign-in moves focus to the first request field in fixture/live modes. Pin Playwright1.63.0 as a dev
only dependency. Also add the focus assertion to the existing deterministic Node wiring oracle.
2. Run the actual browser and Node oracle before implementation.
Expected: sign-in succeeds but keyboard focus does not reach the request input. Retain that failure.
3. Fix only observed focus behavior and any independently observed browser defects. Keep labelled
controls and credential erasure. Rebuild/install clean wheel before repeat browser testing.
4. Run focused page and HTTP tests plus actual browser focus checks.
Expected: both modes focus the request field; all current boundary/review behavior passes. Commit.

## Task 2: Installed fixture and live walkthrough acceptance

Interfaces: Task1 clean installed wheel and browser fixtures; produces redacted reports/screenshots.

1. Freeze exact runtime/wheel/browser/model versions before inference. Exercise all three synthetic
Atlas review scenarios through UI: mismatch, unresolved requirement, missing observation. Use exact
selected ISO cutoff and literal catalog items. Each live demonstration is repeated three times,
reporting all nine attempts rather than independent held-out accuracy.
2. Exercise original-cell/authority drill-down, readable quantities/status, focused brief heading,
keyboard review, repeat approval identity, rejection, lock/reload, unsupported/ambiguous questions,
error recovery, server restart awaiting review and owned history/recovery without new inference.
Verify journal/event/save accounting. Do not issue approval from model/fixture code.
3. Check narrow/wide viewport overflow and selected color/focus/label semantics. Screenshots are
credential-free; no raw browser trace, HAR, request headers or hidden reasoning retention.
Expected: all selected interaction gates pass with retained results; a failure is investigated,
not concealed. These are bounded browser checks, not comprehensive accessibility certification.
4. Document a five-minute local walkthrough and replay instructions, limits and artifacts. Commit.

## Task 3: Verify and publish

Interfaces: immutable browser evidence and unchanged authority; produces handoff/PR semantic evidence.

1. Run makecheck, makepackage-smoke, current/known-bad challenges, plus actual installed browser
acceptance. Synchronize handoff/milestone map and record architecture applicability (no new product
boundary; ADR031/032 controls unchanged).
Expected: required deterministic/package/browser checks pass.
2. One independent whole-branch review using requesting-code-review and semantic reviewer. Correct
Important/Critical findings in one RED/GREEN author pass; defer optional minors.
3. Validate exact-head semantic JSON/PR contract, push a stacked draft, verify CI and live planning.
Update #74/#72 evidence preserving broader criteria/status. No Issue closure or expansion claim.
Expected: reviewable verified draft; all attempted runs and remaining G2/release gates explicit.

## Review Focus

Credential persistence/leakage from automation and screenshots; actual installed public path versus
helper/mocked acceptance; browser races, focus, clarification/failed run recovery, lock/reload; source
membership/highlight and unchanged unknown/conflict values; repeated approval identity, application
ledger versus rendered state, process restart without inference; fresh-version binding and separation
of fixture, live demonstration repetitions, accessibility observations and held-out evaluation.
