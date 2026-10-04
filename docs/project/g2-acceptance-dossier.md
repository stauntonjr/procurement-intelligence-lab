# G2 installed acceptance dossier

Primary #72/M9, part of #53/#67/#68/#70/#71/#73/#74. `codex/g2-evidence-consolidation`
is stacked on draft #189, unmerged. This compiles immutable previously executed reports and adds
one measured installed deterministic HTTP run. It makes no new model request and changes no
runtime/prompt/model/source/gold/package policy. The [frozen manifest](../../evals/operational_agents/g2-evidence-v1.json)
and [compiled results](g2-acceptance-results.json) retain separate populations and source hashes.

The **bounded installed suite passes**. **Full G2/release and B2 expansion remain not ready**:
comprehensive browser accessibility/error recovery, deployed agent walkthrough, a measured
five-minute presentation or labeled recording, integration to main, and broader Issue layer metrics
are unverified here. No release authority or permission to deploy/expand follows from this report.

## What a reviewer can inspect

| Evidence population | Target outcomes | Actual model attempts | Tools / saves | Meaning |
|---|---:|---:|---:|---|
| Fresh v3 language | 48 pass / 0 fail / 0 unknown | 48 real | 56 / 28 | 24 root questions, 24 independently authored; known correlated sources |
| Original browser scenarios | 9 pass / 0 fail / 0 unknown | 9 real | 18 / 8 | Three repetitions of three original January fixtures |
| Adversarial installed guards | 9 pass / 0 fail / 0 unknown | 5 real + 3 controlled | 7 / 1 | One real tool failure retained; controlled model failures are separate |
| Prior baseline controls | 25 pass / 3 fail / 0 unknown | 28 real | See compiled results | Inspected development under the prior prompt/application |
| Candidate controls | 26 pass / 2 fail / 0 unknown | 28 real | See compiled results | Two safe valid-request abstentions remain |
| New deterministic HTTP baseline | 48 pass / 0 fail / 0 unknown | 0 | No agent tools / saves | All 464 original source checks passed |

These rows are not summed into an accuracy score. `evidence_status=pass` means a source report is
present, hash/version compatible and internally reconciled; it does not change its failed target
outcomes. The candidate controls still miss `atlas-before-boundary` (date clarification) and
`borealis-conflict` (unsupported). Historical baseline failures remain in the dossier. The new
language run does not erase them or prove a causal prompt improvement. Independent language is
24 questions, not 48; the original nine runs are repetitions, not nine independent questions.

The original scenarios preserve exact source semantics: mismatch required4/observed2; conflicting
requirements retain observed2 but required unknown and not_assessed; missing observation retains
required4 but ordered unknown and not_assessed. Neither unknown becomes zero or missing PO.
Three process restarts recover the original briefs. Rejection has a completed audit trajectory and
zero saves; approval persists one result. The separate adversarial run proves real exit86 after a
durable save and exact fresh-process/repeated acknowledgment, with original approval bindings.

The model produces literal item/date intent. Deterministic services construct numerical/status
facts and the canonical brief; exact human review and fresh source/receipt checks authorize save.
The demo saves a review brief, not a purchase order or external message. This independent reference
demo makes no claim about Scale AI's internal architecture or production procurement authority.

## Measured timing and cost boundaries

| Population and timing scope | n | Median seconds | p95 seconds |
|---|---:|---:|---:|
| New deterministic investigation HTTP roundtrip | 48 | 0.168 | 0.186 |
| New deterministic source lookup HTTP roundtrip | 464 | 0.167 | 0.184 |
| Fresh v3 model interpretation transport | 48 | 1.158 | 1.243 |
| Fresh v3 public multi-process workflow roundtrip | 48 | 4.127 | 4.298 |
| Original browser model interpretation transport | 9 | 1.142 | 1.489 |
| Adversarial real model interpretation transport | 5 | 1.152 | 1.155 |
| Prior baseline controls model transport | 28 | 0.839 | 1.162 |
| Candidate controls model transport | 28 | 0.859 | 1.187 |

p95 uses nearest rank, ceil(0.95*n); small samples and correlated cases limit its meaning. The new
baseline ran sequentially in one fresh installed inspector process. OS/filesystem/cache warm/cold
state was not measured; a fresh process alone is not a cold-cache claim. Investigation timing includes
admission, deterministic assessment, HTTP and serialization. It includes valid rejection responses;
source timing is separate. Model timing includes the interpretation transport only, not GPU compute
or end-to-end user latency. Public workflow timing includes several CLI processes/recovery/review/save
operations and variable requested work; it is not a measured human five-minute walkthrough.

These distributions cover different tasks/requests/conditions. No speed ratio, causal paired
comparison, hardware superiority, throughput or hard-cancellation conclusion follows. Source requests
are not model or tool calls. Controlled provider responses/usage do not enter real-model timing or
token aggregates. Actual failed model statuses and tool-failed events remain visible separately from
safety-guard results. Model-token usage is provider-reported, not an independent GPU/token meter.
Unobserved usage remains unknown; cost USD remains null rather than assumed free or fabricated.

## Reproduction and evidence boundaries

The compiler only reads evaluator reports. It refuses hash/version/denominator/path drift, checks
score-to-journal ownership and terminal counts, source/fact/save consistency and applicable causal
completion. Missing required records remain unknown, contradictions fail, and unknown calls are null.
A small report cannot silently shrink the closed 48/9/9/28/28/48 role denominators. Empty/missing roles
cannot pass. Exact output replay does not reissue any interpretation or authorize a save.

```sh
.venv/bin/python -m tools.consolidate_g2_evidence \
  --manifest evals/operational_agents/g2-evidence-v1.json \
  --artifact-root /home/jrs/procurement-intelligence-lab \
  --output /tmp/new-g2-dossier.json
```

Use a fresh output. The full raw evidence bundle lives under `artifacts/g2-evidence/v1/` plus the
manifest's historical report paths; artifacts are local/ignored. The checked-in compact results and
manifest retain provenance when raw files are unavailable. Running without the bundle produces
unknown missing groups and a nonzero exit; it does not regenerate or accept missing evidence.
The new timing run used the verified existing clean wheel with100Python source/wheel/installed bytes
and runtime versions equal. Runtime packaging is unchanged; gold/qrels/evaluator manifests remain
outside it. Baseline replay is a new deterministic measurement, not a replacement historical run:

```sh
.venv/bin/python -m tools.consolidate_g2_evidence --measure-baseline \
  --python /tmp/pil-cutoff-env/bin/python \
  --dataset evals/procurement_corpus/fresh-language-v3 \
  --output /tmp/new-deterministic-baseline.json
```

Existing reports cannot be overwritten. Current acceptance contains exactly one new baseline and
zero new inference; its hashes were frozen before compilation. It is structured oracle-bound HTTP,
not natural-language interpretation, extraction/ER/retrieval benchmarking, or a bigger source corpus.
No raw provider reasoning, credentials, tracing/export, model reload or retry is introduced.

## Ordered remaining work

1. Bounded actual-browser asynchronous/error recovery and accessibility evidence for #74: keyboard
   focus, labeled/readable failure states, retained drafts and safe recovery on the installed caller.
   Existing focus/contrast/walkthrough checks are useful but not complete screen-reader/WCAG/device proof.
2. Rehearse/time the five-minute reviewer story and retain labeled screenshots/recording fallback.
3. Integrate/review the draft stack and verify #73's deployment through actual UI/API/agent requests,
   preserving the current inspector with rollback. This report does not authorize merge/deployment.
4. Deliberately reconcile remaining #72/#73/#74 acceptance; broader Issues remain open/In Progress.
5. Only after the release gates, execute approved B2 source diversity:20projects/120documents/4800rows,
   200queries and12/4/4project split with independent gold. Current corpus is still4projects,
   24workbooks and960rows. More wording is not source expansion.
