# Cutoff intent development — 2026-10-04

Primary #53/M5; part of #66/#67/#68/#70/#71/#72. `codex/cutoff-intent-development`
is stacked on draft #186; branch work, no merge/deployment. Implements approved corpus Task5B/5C.

## Contract and hypothesis

A request to set/use the same supplied review cutoff is read-only query metadata, not a procurement
mutation or approval. Different explicit dates/instants still clarify before investigation. Existing
scope/literal-item/proposal guards, deterministic quantity/evidence policy and exact human review
retain authority. The prompt now states that distinction and includes generic contrasting examples;
it contains no case IDs, corpus identifiers or gold. No schema, transport, model, provider, budget,
source dataset or numeric policy changed. See [ADR-032](../adr/032-local-model-intent-and-journal.md).

The prior [fresh-language evaluation](fresh-language-evaluation.md) remains immutable at 47/48.
Its questions are now inspected development data and cannot support new holdout claims after
this prompt experiment. Retired validation/test names in source manifests are historical accounting,
not fresh quality evidence. Require new independently authored wording before later quality claims
or corpus expansion; known synthetic source scenarios still limit independence.

## Frozen experiments

[Controls](../../evals/operational_agents/cutoff-development-v1.json) frozen at 287c3f2: the prior 20
unchanged controls plus eight matching/conflicting cutoff, foreign project, source mutation, direct
approval, mixed injected review/save and alias questions. Candidate prompt frozen at 155df17.
The historical Cinder Set query is explicitly reused. The installed old/new runtime versions were
checked against their frozen checkout before calls. One attempt per case/configuration/run, no retry.

| Run | Outcome | Observed failures |
|---|---:|---|
| Baseline controls | 25/28 | Two valid boundary queries clarified; a conflicting explicit date incorrectly investigated. |
| Candidate controls | 26/28 | One valid boundary query clarified; Borealis requirement conflict unexpectedly unsupported. |
| Candidate inspected-language regression | 48/48 | None; development evidence. |
| Candidate original browser | 9/9 | Three source configurations, three repetitions each. |

The previous Cinder Set miss did **not** reproduce in the baseline repetition. It passed both
candidate controls and candidate regression, too. Temperature0 is not proof of deterministic
inference; these observations do not prove that prompt changes caused every outcome difference.
The candidate passed all negative date/scope/write/alias/multiple/relative controls in this run.
Its two supported-request abstentions are retained, with no tools/save for those cases.
Baseline conflicting-date investigation is a failed target, not an accepted semantic interpretation.
No control test issues approval; both control ledgers contain zero saved results.

Candidate installed structured HTTP48/48 and 464 source checks passed. All28 accepted regression
investigations matched complete deterministic facts, recovered in fresh CLI processes, rejected
altered digests and acknowledged one result after repeated exact approval/save. Twenty expected
abstentions passed without tools/save. The report says development_regression, never fresh holdout.

Original installed Chromium151.0.7922.34 trials passed original policy/assessment/source identities,
18 source checks, three process recoveries and eight exact saves; one investigation was rejected.
An initial browser executable lookup failed **before inference**, retaining nine unknown records.
The corrected run used the existing cached Chromium and fresh output; no model attempt was retried.

[Compact versions/results](cutoff-intent-results.json) retain all outcomes and full-report hashes.
Direct journals reconcile **113 unique actual terminal calls**,124 tool starts and36 saved results:
28 baseline+28 candidate+48 regression+9 original browser. The primary Set question is measured once
in baseline controls and twice in candidate controls/regression, under fresh run IDs. Historical
controls/browser repetitions overlap prior work. These are not113independent questions or a global
one-attempt-per-question claim. Model transport timing is observed, not a speed/throughput comparison.
Concurrent deterministic checks and model runs are not an isolated performance benchmark.

## Reproduction and verification

Build/install a clean optional workflow wheel outside checkout. Control invocation:

```bash
PIL_INTENT_PYTHON=/tmp/pil-cutoff-env/bin/python \
PIL_INTENT_DATABASE=/tmp/pil-cutoff-FRESH.db \
PIL_INTENT_OUTPUT=artifacts/cutoff-development/v1/FRESH.json \
PIL_INTENT_MANIFEST=evals/operational_agents/cutoff-development-v1.json \
.venv/bin/python -m pytest -q tests/integration/test_live_intent_development.py
```

The default remains the prior 20-case manifest; selected manifest hashes and complete denominators
are retained. Failed controls intentionally return nonzero after recording outcomes. Regression:

```bash
.venv/bin/python -m tools.run_g2_pilot --run-live \
  --python /tmp/pil-cutoff-env/bin/python \
  --dataset evals/procurement_corpus/fresh-language-v2 \
  --manifest evals/operational_agents/cutoff-language-regression-v1.json \
  --database /tmp/pil-cutoff-regression-FRESH.db \
  --output artifacts/cutoff-development/v1/regression-FRESH.json
```

No old artifacts are overwritten. Actual model/approval/restart/source checks use clean installed
wheel c6abc43be4f5d0e5fbe4113bb07914ee9d57c152d0998d5777ad844db7a7051e.
Wheel prompt bytes match checkout and evaluator gold is excluded. Frozen model/provider/schema
remain unchanged; new prompt/application version identities refuse old run recovery.

`make check`:666 passed,10 explicit opt-in skips,88.15% coverage/ratchet,strict types/static/architecture.
`make package-smoke` and C001-C017 current-code/known-bad checks passed. No newly shipped semantic
defect or deterministic natural-language oracle is claimed for this unmerged prompt experiment.

## Remaining limits

Global completion remains **not_ready** because two valid control requests still abstain; a green
48-case development regression does not establish full G2 or unscripted language reliability.
Preserve all observations and avoid tuning/relabeling a cohort as untouched. Fresh independent
language evaluation, remaining full G2/adversarial release gates, comprehensive accessibility and
deployment are separate work. Corpus expansion remains gated. No paid provider/model reload/traces.
The latest roadmap advisory remains the prior daily-quota429 failure37189328482; this bounded
continuation deliberately reviewed live Project/planning state and does not claim a new advisory.
