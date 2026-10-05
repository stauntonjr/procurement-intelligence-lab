# Installed browser review acceptance — 2026-10-04

Primary #74/M9; Part of #53/#67/#68/#72/#73. `codex/browser-live-acceptance` is stacked on
PR #183. This is branch evidence; `main` remains `b0cc77e`. No merge or deployment.

The interactive computer-use connector returned no apps or browsers. Cached ARM64 Chromium
151.0.7922.34 runs locally through pinned development-only Playwright 1.63.0. The actual
browser submits to a separately installed wheel server, launched from `/tmp`, and reads
persisted application records after a real server restart. No HTTP test double substitutes
for the browser or local Qwen. ADR-031/032 boundaries and prompt are unchanged.

## Observed defects and corrections

Actual Chromium and the existing Node page oracle first reproduced successful sign-in without
focus on the request input. Both fixture/live pages now focus it. The former custom focus
ring measured 2.237:1 against white; the darker ring passes the selected 3:1 check. Narrow
375px rendering exposed the unbroken brief SHA-256 extending the page to 654px. Review
identifiers and digests now wrap. Fresh installed wheel checks cover these fixes.

The [W3C non-text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
and [text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
define the selected checks. Measured normal text in the facts, approve button and muted
workspace copy passes 4.5:1. These selected checks do not certify full WCAG compliance.

## Frozen walkthrough evidence

[Compact results, versions, run IDs and artifact hashes](browser-live-results.json) retain
all outcomes. The authored [manifest](../../evals/operational_agents/browser-walkthrough-v1.json)
was committed before live inference. Installed composition hashes match the checkout; each
journal/event/save is joined by run ID and checked against the submitted question hash and
versions. Reports and credential-free wide/narrow screenshots live under
`artifacts/browser-live/v1/final/{fixture,live}/`. No browser traces, HAR, request headers,
raw model output or hidden reasoning are retained. Disposable token files are removed after
the owned servers exit.

- Fixture: three scenarios, 32 source/authority checks, six tool starts, two saved briefs;
  unresolved requirement is rejected and stays unsaved.
- Live: nine investigations (GPU-A/GPU-C/GPU-D, three repetitions each), four abstentions,
  one read request with injected automatic approval/save instructions; all 14 pass their
  authored interaction expectations. 108 source/authority checks pass. Ten investigations produce 20 tool starts and eight
  saved briefs. Human rejection leaves unresolved-r1 and the injected-command run unsaved;
  the model never approves or saves. All four abstentions invoke zero tools.
- All displayed source cells and highlighted columns match their authenticated response;
  authority records match exactly. Missing and unresolved quantities remain explicit unknowns.
- Keyboard submission, focused brief heading, source buttons, approve/reject and lock are
  exercised. Review rejects an altered digest; repeated approval acknowledges the same save.
  First mismatch survives process restart and owned-history discovery/recovery with no new
  inference. Lock clears the workspace; reload requires sign-in. No cookies/local/session
  storage, credential URLs, external page requests or JavaScript runtime errors observed.
- Wide 1280px and narrow 375px screenshots pass horizontal reflow and were visually inspected.
  Reflow assertion is an authored representative state, not every possible corpus value.

Three fixture failures are retained: relative output path in the new harness prevented server
startup; an authority assertion expected a nonexistent `record_key`; actual digest overflow
required a product fix. A fourth fixture pass preceded the added text/reload checks; the final
fixture pass covers both. None invoked inference. Task1 RED failures and focused GREEN checks
are retained in the local logs. These development corrections do not alter the frozen original
41/48 pilot or inspected 46/48 intent-development regression.

## Five-minute interview walkthrough

Use the installed local live command from [the public contract](../product/local-qwen-review-v1.md)
with a fresh database, `--project atlas`, private token file and selected loopback endpoint.
Keep the token off shared displays; enter it before recording and confirm the input is empty.

1. **0:00–0:40:** Explain model evidence versus deterministic policy and human authority.
   Identify synthetic corpus, project and exact selected cutoff. Show the live badge and versions.
2. **0:40–2:00:** Submit the manifest GPU-A question at `2026-10-01T00:00:00Z`.
   Show required 8 versus ordered 6, then original XLSX cells, highlighted columns and governance
   records. Distinguish source evidence from the application execution timeline.
3. **2:00–2:50:** Restart the owned server with the same database/context/configuration.
   Sign in, select history and recover. Show the same brief digest; approve it and demonstrate
   the same saved identity on repeat approval. Approval saves a demo brief, never a purchase.
4. **2:50–4:00:** Submit GPU-C then GPU-D. Explain unresolved requirement versus missing
   observation. Reject GPU-C; show that no save occurred and unknowns did not become zero.
5. **4:00–5:00:** Ask the ambiguous GPU question, then the injected-command question.
   Show clarification has no tools/brief; the injected command cannot save without human review.
   Reject it. Close with retained failures, inspected-data limits and remaining release gates.

This timing is a proposed rehearsal script, not a measured presentation or recorded video.

## Replay and remaining gates

Build and install a clean wheel with optional workflow dependencies into a separate environment;
keep checkout paths out of the server's working directory. Normal CI skips actual browser/model
runs. Use cached/explicitly installed Chromium and a fresh evidence output directory:

```sh
PIL_BROWSER_PYTHON=/path/to/clean-wheel-env/bin/python \
PIL_BROWSER_EXECUTABLE=/path/to/chromium \
PIL_BROWSER_OUTPUT=/tmp/fresh-browser-evidence \
uv run --extra workflow pytest -q tests/integration/test_browser_review.py
```

This runs the three focus checks and fixture walkthrough; live is skipped. Add
`PIL_BROWSER_LIVE=1` and select `test_installed_browser_walkthrough[live-walkthrough]` for
exactly 14 actual local model submissions. Endpoint selection remains the existing loopback
CLI contract; never point this harness at a paid provider implicitly. Preserve old output.

Fresh frozen held-out evaluation, original tiny-fixture live routing, full G2 acceptance,
public deployment/production authentication and final integrated release remain separate.
The existing four-project, 24-workbook, 960-row corpus is unchanged. Dataset expansion stays
gated. The roadmap advisory run
[37178219019](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/37178219019)
failed Gemini daily quota (429); no usable advisory report is claimed. Live Project audit is
recorded separately; #74/#72 remain open with broader acceptance incomplete.

## Deterministic verification

`make check`: 612 passed, six explicit opt-in skips, 88.28% coverage and ratchet; strict
format/lint/types, architecture and harness/supply-chain checks passed. The five new opt-in
browser cases were separately executed against the installed wheel (three focus checks and
fixture/live walkthroughs); the inherited live intent-development case remains opt-in.
`make package-smoke` passed isolated base/optional installs and advertised commands.
`make challenges` passed C001-C017 with every known-bad mutation rejected; no agent performance
claim. Final reviewed revision, review disposition and CI are bound in the draft PR evidence.

## Independent review

One independent read-only review of `7197b58fafb91c195ad28b54d8794046b8f53567` found no
Critical or Important issue and reconciled compact/source/SQLite/screenshot/wheel evidence.
One optional Minor is deferred: the three focus-only tests leave private generated token files
in pytest temporary directories after their owned servers stop. Walkthrough token files are
removed. This is test credential cleanup; no active capability leak was observed. Full device,
screen-reader and WCAG coverage, production authentication, held-out language quality,
tiny-fixture live routing and exhaustive asynchronous/draft-failure browser recovery remain
open. Existing HTTP/Node failure/race tests are not substituted for those browser claims.
Final documentation-only updates and exact-head evidence receive an author fresh pass; no
second independent review or extra inference is performed.
