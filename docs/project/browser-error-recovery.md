# Installed browser error recovery — 2026-10-04

Branch `codex/browser-error-recovery` stacks on draft #190, unmerged and undeployed.
Primary #74/M9; part of #53/#67/#68/#70/#71/#72/#73. This implements the bounded error/async
continuation in approved corpus plan Task5B/5C and browser-live plan Task2. Existing ADR-029,
ADR-031 and ADR-032 govern authority and transport; no architecture or decision-policy change.

The public caller is Chromium151.0.7922.34 with pinned Playwright1.63.0, operating a clean wheel
installed outside the checkout. The frozen [twelve cases](../../evals/operational_agents/browser-recovery-v2.json)
and [compact results](browser-error-recovery-results.json) bind application
`sha256:38417accf2c31350b5f1f1a98ac5b1e36e70f4a27bfc9e761da27f2786c0fd4a` and wheel
`9e30d46a10e274639b9acb75eb9f320e9700ea2ebed196644753226497d39343`. All100Python source,
wheel and installed bytes match. These twelve authored cases pass; eight fixture runs, sixteen tool
starts, one durable save and zero interpretation calls reconcile directly with owned SQLite.
Repeated GPU-A fixtures are correlated and cannot establish model quality or corpus diversity.

## Public behavior and authority

A failed replacement retains the selected exact persisted brief, prior timeline and explicit
human review/recovery. Edited request inputs are retained but cannot authorize review of a new
brief. The old brief's item/as-of/run/digest remains visible. New canonical success clears the old
timeline; an abstention clears prior canonical authority. Unknown acknowledgment never means a
save failed and never triggers automatic POST/model retry.

Successful payloads are parsed and structurally validated before any review or interpretation
state changes. Malformed JSON, private error/code payloads and transport exception details never enter the
visible error. Page-owned safe text maps HTTP dispositions; server typed DTO failure boundaries
remain unchanged. A delayed callback checks session epoch before follow-up timeline/history
requests. Lock invalidates page callbacks and clears local authority; it does not cancel a
request already admitted by the server or revoke its capability.

Lost save acknowledgment is tested after the actual backend commits an exact human review.
Explicit recovery returns the same SavedBrief identity/digest; a repeated human approval returns
that same single saved result without more investigation tools. Source/read failure preserves
prior exact review and known source content; explicit recovery focuses the review heading.

## Observations and controls

| Case family | Actual backend evidence | Controlled browser fault |
|---|---|---|
| Failed replacement | One persisted prior fixture draft; no replacement run/save | Start503 before backend |
| Malformed200 replacement | Prior exact draft, captured unchanged review POST and actual owned recovery | Three invalid nested payloads and review503 before backend |
| Text/JSON error, both pages | No run/save; live interpretation journal empty | Four responses intercepted before start/ask backend |
| Lock during timeline | Actual persisted draft and fetched event response | Hold response until lock; no late follow-up request |
| Lost save acknowledgment | One actual save, recovery and repeat exact review | Drop browser acknowledgment after actual durable commit |
| Source failure | Actual prior source read and same persisted draft | Later source read503 before backend |
| Selected-run read failure | Actual prior draft and explicit same-run recovery | Selected read503 before backend |

The live page is UI-only in this slice: ask is intercepted before inference. No provider quality,
Qwen availability, model latency, workflow benchmark or cost measurement is inferred. Raw local
bundle `artifacts/browser-recovery/v2/` is ignored, with freeze/parity, case reports, databases,
logs and two credential-free screenshots. Compact tracked hashes identify retained reports;
missing local artifacts are unavailable evidence, not reproducible model outcomes.

The375px retained-draft error screenshot and1280px recovered-save screenshot were visually
inspected: readable wrapping, no horizontal overflow, old GPU-A identity while GPU-C request is
retained, and a visible saved identity/focused review. Error text contrast8.53 exceeds4.5.
Token inputs were erased before screenshots; local/session storage and cookies are empty.
This is bounded evidence, not a comprehensive accessibility conformance claim.

## Regression and verification boundary

Observed installed RED: lost old draft, private malformed text/valid JSON error, and late history
request after lock. C018-C021 restore those defects and reject the known-bad revision; all21
current challenge oracles pass and reject known-bad mutations. Node checks exercise shipped JS
semantics but are distinct from the actual installed twelve-browser-case acceptance17.42seconds.
Clean package smoke passed. Full latest-revision checks and independent review are recorded in
the draft's semantic evidence, rather than inferred from these focused passes.

All development attempts are retained separately under `development/`: initial delayed-event
race and hidden-control locator failures were harness failures; the first added JSON probe
accidentally tested text and passed, so is not a JSON RED. Corrected JSON and delayed-event probes
then failed on the intended product assertions. First rebuilt run failed three hidden-role
lookups; corrected DOM selectors yielded9/9. First frozen nine-case run passed at the pre-review application version; it remains immutable in
`artifacts/browser-recovery/v1/` and its v1 manifest. The sole independent review found malformed200
replacement state/privacy failure; four Node and three installed browser RED cases reproduced it.
The correction validates nested fixture/live payloads before state changes, and exposes only
page-owned errors. A separate v2 twelve-case population verifies the corrected runtime. One attempted
v2 run used the old install after a pip-unavailable installation failure: parity rejected it before
acceptance; its9passes/3failures are retained under `unqualified-old-install/`. uv installed the
correct wheel before the separate frozen final run. A challenge selector ambiguity was corrected
without changing the legacy oracle; no artifact is overwritten or treated as successful acceptance. None made
an inference call. Harness failures and rejected attempts are not silently removed.

Application hashing includes the page, so prior G2 model/browser reports at `afe3ae...` remain
historical. Their passes are not current-version live acceptance of sha256:38417accf2c31350b5f1f1a98ac5b1e36e70f4a27bfc9e761da27f2786c0fd4a. Full G2/release,
current-version live walkthrough, measured five-minute presentation, comprehensive accessibility,
main integration and deployment remain open. B2 corpus expansion remains gated; the corpus stays
four projects,24workbooks,960rows. Next work is bounded reviewer rehearsal and a separately scoped
current-version live acceptance check before rollout or expansion.
