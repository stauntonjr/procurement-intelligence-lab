# Demo integration review fixes

Primary #72/M9, part of #66/#67/#68/#70. Branch `codex/demo-integration-review-fixes`
was developed on draft #192. The consolidated draft targets `main` and includes the entire stack plus these fixes; the historical PRs remain open pending integration. No merge, deployment or model inference is performed by this slice.

## Integration audit

The eighteen open demo PRs #175–#192 form a linear ancestor chain; every exact head had all
ten current deterministic check names passing when inspected. Three historical roadmap `audit`
checks failed; these are advisory and are not represented as passing required checks.
Six unresolved automated review threads remained on #176–#178. Green CI did not discharge them.
Snapshots, full review threads and ancestry results are retained under `artifacts/demo-integration/v1/`.

## Confirmed review defects

| Review | Correction and oracle |
|---|---|
| #176 failure accounting | Non-applicability cannot erase recorded failure or partial execution; C022. |
| #176 completion chronology | Completion must follow all recorded timestamps and close the recorded causal path; C023. |
| #176 immutable revision | Run/brief CLIs hash installed Python paths/bytes like the workflow; unchanged package version is insufficient; C024. |
| #177 tool output | Validate complete shared application payload and snapshot before durable success; malformed results retain typed failed invocation; C025. |
| #178 saved-version replay | Supersession blocks new writes, while completed exact writes return their existing result after source/authority revalidation; C026. |
| #178 vanished item | Missing previously reviewed item maps to stale brief conflict, never traceback or saved result; C027. |

All quantities, policies, permissions, source inventory, prompt and selected model remain unchanged.
The application hash changes with these fixes. Prior current-version live walkthroughs retain their
original revision and become historical; no inference was repeated here. Fixture results and
known-bad challenge mutations are not model-quality or new source-diversity evidence.

## Validation and remaining gates

Six new regressions first failed with 52 existing focused passes. The first focused repair suite
passed 61 tests. New public CLI cases exercise replaced saved acknowledgment and vanished-item
error translation through the shipped entry point. Clean built package smoke passes; six public
challenges pass and reject known-bad equivalents. Independent review of 0cc22d6 identified two Important gaps: active-ledger corruption during saved replay, and nested investigation fields outside validation. Five new regressions failed, then a root corrective pass and 65-test focused suite passed. Shared application payload serialization (ADR-033), including malformed nested output through the real CLI, and missing/dangling/foreign active-pointer checks close those gaps. No second independent review was requested. Final `make check`: 763 passed, 22 explicit opt-in skips, 411.65 seconds; 88.98% branch coverage, coverage ratchet and architecture checks passed. Final clean-package smoke, all 27 current/known-bad challenges and 13 clean-installed fixture/browser cases passed. The 102 Python files match source/wheel/installed bytes. [Compact results](demo-integration-review-results.json) retain the application/wheel hashes.

A failed challenge setup (non-unique mutation and outdated fixed ID inventory) and two static typing
findings were corrected before the full test run. A roadmap dispatch against the not-yet-published
branch failed with missing ref; the read-only audit was subsequently dispatched against #192's
published branch. The advisory audit failed again on Gemini daily quota 429; its exact log is retained and no usable report is claimed. The full suite was interrupted after the review found new gaps, then restarted after corrections. An initial installed-browser selector used the wrong fixture case ID and collected no tests; the corrected selector runs the shipped fixture case. These are setup/interrupted runs, not passed product acceptance.

Full G2/release, human timed rehearsal, comprehensive accessibility, integration on main and
separately authorized deployment remain open. Corpus remains four projects, 24 workbooks and
960 source rows; the 20-project expansion remains gated.
