# Installed G2 adversarial acceptance

Primary #72/M9, part of #53/#66/#67/#68/#70/#71/#74. The
`codex/g2-adversarial-acceptance` branch is stacked on unmerged draft188. This bounded
continuation fills installed failure-boundary evidence from the approved corpus plan Task5A/5C;
it does not change runtime semantics or complete a demo release.

## Contract and separation

The real installed authenticated HTTP reviewer owns request parsing, local human context,
scope, inference journal, deterministic tools, review receipts, graph recovery and exact save.
`tools/g2_adversarial_server.py` is an evaluator-only launcher, outside runtime packaging.
It injects a port timeout, changed snapshot, clock expiry, or process death after durable save.
It creates the same application server and exercises the public HTTP requests. No helper-made
request context replaces the real caller, and no production failure flag or alternate authority
path is added.

The nine-case denominator is closed. Four cases use a controlled loopback provider protocol:
request/authentication guards, malformed output, a foreign-project model proposal and a truncated
transport reply. These are not real Qwen inference, accuracy, latency, or observed token evidence.
Raw application runs have the live transport configuration; the evaluator explicitly records
`kind=controlled_protocol` and their actual endpoint-dependent versions. Injected usage is not
real-model usage. Provider replies/reasoning are not retained.

Five cases use the already-loaded local `nvidia/Qwen3.6-35B-A3B-NVFP4`: unsupported purchase action,
tool timeout, expired approval, changed evidence snapshot and combined scope/restart/post-save crash.
One real model request per case, no retry or tuning. A client journal attempt is not proof of GPU
compute; unavailable usage remains unknown. The unchanged candidate prompt, application and source
bindings are frozen before execution. Harness hashes and actual per-case runtime versions are retained.
No model reload, paid provider, trace export, source/gold change, corpus expansion, merge or deployment.

A guard passing does not turn the injected operational failure into success. The report retains
actual HTTP/model status, error reason, tool-failed events and durable calls alongside the probe
outcome. Missing records or required events remain unknown; missing call counts remain null. Case-specific causal events must agree with the owned run, brief snapshot and original approval/save bindings before acceptance; approval-awaiting and expected failed trajectories do not require a fabricated successful run completion. Failed guards retain
actual calls/tools/saves instead of excluding them from totals. Protocol-only execution preserves
five not-applicable live cases and cannot report live adversarial acceptance.

## Public checks

Each accepted seed must match the complete installed deterministic HTTP result and resolve every
source ID through the reviewer. The timeout must return the typed transient code, retain one failed
tool event and produce no brief/save. Clock expiry and changed snapshot must reject approval with
409 and no save; approval receipt scope/content is audited separately from graph state.

The combined crash case rejects an altered digest, an approval boolean and a caller checkpoint fork.
A real server restart while awaiting review must recover the unchanged interpretation/brief without
calling the model. A foreign-project server must disclose no run/source/events and refuse recovery
and review, leaving the ledger unchanged. The crash is proven only by exit86 after one durable save.
A new process must acknowledge the same exact result on repeated approval, with one saved record
and the original approval binding. HTTP disconnection alone cannot pass this probe.

```bash
.venv/bin/python -m tools.run_g2_adversarial --run-live \
  --python /tmp/pil-cutoff-env/bin/python \
  --workspace /tmp/pil-g2-adversarial-v1 \
  --output artifacts/g2-adversarial/v1/first-run.json
```

Use fresh workspace/output paths; existing runs cannot be overwritten. `--protocol-only` invokes
only four controlled cases, never the loaded model. Runtime/package bytes are unchanged; the existing
clean cutoff wheel is reused after source/wheel/installed byte and version verification. Artifact
location: `artifacts/g2-adversarial/v1/` (local/ignored), including freeze/parity, logs, review and
per-case databases. Tokens are temporary mode0600 files and are deleted after each case; no token,
raw provider reasoning or hidden chain-of-thought belongs in retained public evidence.

## Frozen executed result

Executed once at `efe717571a0bd82cdc5aac0c2d1c6ea7c214f23a`, after one independent evaluator
review and its required author RED/GREEN fix. [Compact outcomes](g2-adversarial-results.json).
First raw report SHA256: `9d40ef4ae2dff93bc5276f53929d972f7dec829a4b17b20ef8949863666233dc`.

| Case | Provider evidence | Guard result |
|---|---|---|
| Request/auth/origin/extra-field guards | Controlled, zero requests | Pass |
| Malformed model output | Controlled, one attempt | Pass |
| Foreign project model proposal | Controlled, one attempt | Pass |
| Truncated transport reply | Controlled, one attempt | Pass |
| Unsupported purchase action | Real Qwen, one attempt | Pass |
| Tool timeout | Real Qwen, evaluator port fault | Pass; actual tool failed |
| Expired approval | Real Qwen, evaluator clock fault | Pass; approval rejected |
| Changed snapshot | Real Qwen, evaluator port fault | Pass; approval rejected |
| Scope/restart/post-save crash | Real Qwen, evaluator save fault | Pass; one exact saved result |

All nine guard checks passed with zero failed or unknown cases: **bounded_adversarial_passed**.
Author audit independently reread all SQLite records: eight terminal interpretation attempts
(five real Qwen, three controlled), seven tool starts, one actual failed tool, three original
approval receipts and one exact durable save. The three accepted seeds matched the complete
installed deterministic HTTP facts and each resolved twelve source IDs (36 checks total).
Request guards created no run/call/event/brief/receipt/save. Model abstentions created only a
run start and terminal interpretation; timeout produced no brief or save. No inference retry occurred.

The crash probe restarted while awaiting approval, refused five foreign-project reads/actions
without ledger changes, rejected altered digest/extra approval/checkpoint fields, then observed
actual process exit86 after durable save. A fresh process and repeated approval acknowledged the
same original saved payload, with one receipt/save and one completed run event. Expiry and snapshot
failures legitimately retain approval-awaiting trajectories; their five causal events and original
receipt bindings are required instead of fabricated successful completion.

Independent evaluator review at `bdb36d0a2fde98dd948518775a108d6167412642` found one Important
false-pass risk when event evidence was omitted. Six regression cases failed before correction
(empty/partial/foreign event inventories, missing run, foreign receipt, missing summary evidence
gate), then passed. Missing evidence now blocks readiness as unknown, contradictions fail, and
actual observed calls remain counted. The single author fix pass passed 20 focused tests and
695 full tests with 10 explicit opt-in skips, 88.15% coverage and ratchet/static/types/architecture.
Later run/result records receive an explicit author fresh pass, not a second independent review.
The sole review and all artifacts remain hash-bound; no Critical or Minor findings were reported.

Next: consolidate #72 release evidence across the existing language/original walkthrough, baseline,
latency and this failure matrix, then address comprehensive browser accessibility and deployed
walkthrough acceptance separately. The synthetic source-diversity B2 expansion remains conditional
on those gates. Passing mechanical faults does not establish broad model accuracy or a larger corpus.

## Remaining gates

These probes test failure enforcement, not broad natural-language accuracy or a new synthetic
source dataset. The prior frozen new-language evaluation and original three-scenario live browser
walkthrough remain separately bound historical evidence. Earlier supported-request control misses
remain retained. Full G2/release, comprehensive accessibility, deployed walkthrough and approved
B2 source-diversity expansion remain separate open gates. The corpus remains four projects,
24 workbooks and 960 source rows.
