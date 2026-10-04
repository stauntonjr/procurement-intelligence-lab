# Local Qwen review execution evidence

Primary #53/M5; Part of #72/#66/#67/#68/#70/#71. Branch stacked on the browser-review draft.
Main remains `b0cc77e`; no merge or deployment is represented by this record.

The user selected the currently loaded Qwen 3.6. Local model discovery returned
`nvidia/Qwen3.6-35B-A3B-NVFP4`; vLLM version `0.23.1rc1.dev1353+g81f51a780.d20260721`.
No provider credentials, model reload, GPU allocation changes or trace export were used.
Prompt/schema/endpoint/budgets/framework/tool/fixture/application versions are immutable per run.

## Reproducible checks

- Strict proposal, local transport, journal, scope/version and actual CLI/HTTP tests cover accepted,
  malformed/extra/duplicate output, unsupported/clarification, unknown interrupted attempt,
  accepted-before-checkpoint crash, actual tool-timeout event and absent usage.
- Installed wheel probes exercise the native fixture path and new live-intent CLI with a clearly
  labeled deterministic model transport double. Those calls are excluded from live metrics.
- Explicit actual-inference runner `tools/run_live_review_acceptance.py --run-live --python
  /tmp/pil-qwen-acceptance-env/bin/python --database /tmp/pil-qwen-final2-walkthrough.db
  --output artifacts/local-qwen/walkthrough.json` invokes a clean installed wheel from `/tmp`.
  Frozen development manifest: `evals/operational_agents/local-qwen-walkthrough-v1.json`.
- Nine actual live walkthroughs (GPU-A mismatch, GPU-C unresolved requirement, GPU-D missing
  observation, three repetitions each) matched complete canonical facts from the deterministic
  service. Every run recovered through a new CLI process, rejected altered digest, approved and
  acknowledged the same save on repetition. Nine durable saved results; two actual tool calls/run.
  Model elapsed times were 1.068–1.117 seconds (median 1.077). This measures inference transport,
  not complete CLI startup, graph, evidence loading or human review latency.
- Four actual live abstentions passed: unrelated stock-price question, ambiguous item, relative
  date, foreign project. Each retained its inference outcome and invoked zero tools.
- Installed authenticated live HTTP probe `tools/live_review_http_probe.py --run-live --python
  /tmp/pil-qwen-acceptance-env/bin/python --output artifacts/local-qwen/live-http.json` covers a
  separate live question, authenticated start, process restart, recovery and repeated exact save.
  The final probe additionally verifies every source through the actual authenticated HTTP route
  and altered-digest rejection. This is HTTP evidence, not browser acceptance.

Compact durable outcome/versions/run IDs are in [local-qwen-live-results.json](local-qwen-live-results.json). Full local bundles remain under `artifacts/local-qwen/`.

## Retained failures and limits

Initial clean-venv invocation incorrectly resolved the Python symlink to the system interpreter.
Nine commands failed before live inference; retained `artifacts/local-qwen/preflight-failed-walkthrough.json`.
The first development prompt failed three clarification expectations. The nine investigations
otherwise matched facts and saved, but the evaluator referenced `result_id` instead of `saved_id`.
Retained `artifacts/local-qwen/development-prompt-v1-failed.json` includes these outcomes. A separate HTTP paraphrase returned no workflow after the prompt update; its outcome metrics were not captured and are unknown. The final HTTP probe uses the exact development-manifest question and now persists outcomes before assertions. This is an unresolved language-quality limitation, not an authorization bypass. Prompt
revision used only declared development smoke questions; no held-out quality claim or tuning on
validation/test data. Transport diagnostic probes are separate from the acceptance denominator.

An inherited unmerged reviewer-page defect also displayed `result_id`. The executed shipped-JS
oracle failed on the missing saved identity, then passed with `saved_id`. C017 retains this defect
and a known-bad mutation; no development-agent performance score is claimed. Node is needed to
execute that public JavaScript oracle; a unit wiring simulation is not a browser.

Computer-use inventory returned no apps/browsers. Keyboard, focus, contrast, responsive rendering,
real browser interaction, deployed release, original tiny-fixture live routing and full G2 frozen
pilot/held-out evaluation remain open. Corpus expansion is still gated; these 13 development cases
cannot establish broad interpretation accuracy or justify embedding/model superiority.

The read-only roadmap stewardship run [37168612611](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/37168612611)
failed with Gemini daily-quota HTTP 429. No usable advisory report is claimed. Deliberate Project
review found #53/#66/#67/#68/#70/#74 In Progress; #71/#72 Todo at orientation. Planning changes are
verified separately; broader Issues stay open and branch delivery remains distinct from main.

Latest revision-bound JSON, full deterministic/clean-package/challenge results and independent review
are published with the implementation PR. Final evidence is tied to the PR head, not this narrative's
historical timing numbers if implementation subsequently changes.
