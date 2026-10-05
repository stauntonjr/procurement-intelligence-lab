# Browser error recovery implementation plan

> For agentic workers: use superpowers:executing-plans inline for the authorized continuation.

Goal: demonstrate safe asynchronous/failure recovery in the actual installed reviewer browser.
Architecture: existing loopback browser/HTTP/runtime and exact human-review policy; no new subsystem,
model tool, runtime authority or ADR. Primary#74/M9; Partof#53/#67/#68/#70/#71/#72/#73.
Spec: ../specs/2026-10-03-procurement-demo-corpus-design.md and parent corpus plan Task5B/5C;
existing browser-live-acceptance plan Task2 and Issue74 error/focus/recovery acceptance.
Stack on draft190 at5d198dc. No merge/deployment/expansion or new inference.

## Global constraints

Cached Chromium151 / pinned Playwright1.63.0. Actual wheel installed outside checkout; real fixture
HTTP/workflow/save/recovery, injected browser transport faults explicitly controlled, never model
quality. Live page error/lock checks are UI-only and intercept ask before inference. No provider
call, retry, model reload, trace/HAR, raw headers/reasoning or credentials in artifacts/screenshots.
Disposable private tokens erased after owned server exits. Retain all attempted runs and failures.
Unknown POST acknowledgment does not imply failure or permit automatic retry; explicit owned
recovery and human repeated review must bind the same durable result. Lock invalidates page
callbacks; it is not server cancellation. Changed package application hash leaves previous live
G2 evidence historical, not acceptance of this new revision. Broad accessibility/deployment,
measured presentation and B2 remain open.

## Task 1: reproduce and correct bounded browser failures

Files: tests/integration/test_browser_recovery.py using existing installed browser helpers;
tests/unit/test_review_page_recovery.py and Node probe; interfaces/review_page.py only for observed
faults; development-agent challenges and registry for defects if corrected.
Produces bounded UI behavior, regressions and source-wheel build for Task2.
- [ ] Actual installed browser RED: failed replacement draft must retain prior exact brief/recovery;
  malformed response must not expose private response fragments; lock during delayed timeline must
  cause no follow-up requests or restored authority. Both fixture/live page error wiring covered,
  with live ask intercepted before inference. Unit oracle mirrors these semantics, not browser proof.
- [ ] Test actual source failure keeps draft; failed selected-run read remains recoverable;
  actual durable review followed by dropped acknowledgment recovers same saved result and repeat
  human approval yields one save. Verify SQLite run/event/save counts, zero interpretation calls,
  empty credential storage and no late callbacks changing locked state.
- [ ] Correct only reproducible defects, rebuild/install clean artifact and rerun actual browser
  and Node regressions GREEN. Add one challenge per corrected defect, current/known-bad oracles.
  Commit code/tests/challenges; no independent per-task reviewer.

## Task 2: installed evidence and one final review

Files: evals/operational_agents/browser-recovery-v1.json; durable compact results and evidence doc;
ignored artifacts/browser-recovery/v1 for logs/version-bound observations/screenshots.
Consumes Task1 installed package and closed browser case set.
- [ ] Freeze case IDs/runtime/wheel/browser versions; execute bounded actual browser acceptance,
  retain all attempts separately from model quality. Inspect actual journals and credential-free
  screenshot; document exact injected versus backend observations and timing nonclaims.
- [ ] Run package smoke and affected current/known-bad challenges. One independent whole-branch
  review; one author Critical/Important RED/GREEN fix pass, no second review. Final makecheck must
  pass at the final revision before publication; fresh installed retest for runtime changes.

## Task 3: synchronized draft closeout

Files: handoff/milestone map/product contract/evidence documentation; immutable prior reports unchanged.
- [ ] Record bounded passes, historical live-version limitation and remaining browser/release gates.
  Exact-head author semantic fresh pass and schema-valid PR evidence. Push stacked draft, keep
  Issues open/InProgress, verify latest required CI and postwrite live planning. Archive only own
  scratch. No merge/deployment/B2 expansion.

## Review focus

1. Failed/malformed replacement cannot erase the prior exact persisted draft or falsely report success.
2. Lock/re-authentication cannot reuse stale callbacks, expose prior-session facts, issue new requests
   under a different capability or mutate current review; no cancellation or automatic-retry claim.
3. Interrupted save acknowledgment remains ambiguous until actual owned recovery; one durable save,
   exact receipt/digest identity, explicit human approval and no model/fixture authority sharing.
4. Actual installed browser and backend proof remain distinct from injected HTTP/Node controls;
   fixture and live-page-no-inference states never enter model quality or timing aggregates.
5. Credentials/private response fragments stay out of UI/artifacts; unknown source/quantity meanings
   unchanged. Historical G2 hashes preserved; package/version changes cannot silently inherit acceptance.
