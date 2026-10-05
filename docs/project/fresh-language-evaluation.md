# Fresh language evaluation over known source scenarios

Primary #72/M9, part of #53/#70/#71. `codex/fresh-language-evaluation` is stacked
on draft PR #185; unmerged branch work. Approved parent: corpus plan Task5A/5C and
its retired-test rule. This increment measures new wording without changing runtime,
prompt, model, source scenarios or numerical oracles.

The four original projects and all earlier questions are inspected development data.
New [question dataset](../../evals/procurement_corpus/fresh-language-v2/queries.json)
and [interpretation manifest](../../evals/operational_agents/fresh-language-v2.json)
retain exact original project/category/item/cutoff/scenario metadata. Existing independently
audited gold and qrels are copied byte-for-byte, not new facts or corpus expansion.

Atlas/Borealis: 24 root-authored development questions. Cinder/Delta: 12 validation and
12 test questions authored in a fresh independent context before exposure to previous
questions, per-case model results or production prompt. The same reviewer then reviewed
this evaluator increment; the author file was not changed after exposure. The
[immutable author record](../../evals/procurement_corpus/fresh-language-v2/independent-language-author.json)
SHA256 is `c733b676db52d2f138347aa29e4e040211db0b8b29c0fc5d76e69a567aeac004`.

This is a language-only holdout over known, correlated source/scenario families and
vocabularies. It is public and does not establish secret/blind evaluation, new project/data
independence, statistical sufficiency or broad model accuracy. Once the new results are
inspected for tuning, retire this version as language development data. Do not tune and
rerun it while preserving its held-out label.

## Execution and integrity

Runtime was frozen before authoring at application revision `55bac5c`; application binding,
model `nvidia/Qwen3.6-35B-A3B-NVFP4`, prompt/schema/tool/corpus versions are in the manifest.
No model reload, provider change, paid calls or trace upload. One attempt per 48 cases, no retry.
Every interpretation uses a fresh owned run; only question/project/selected cutoff reach
the public live CLI. IDs, expected interpretation labels and structured oracle values never
enter model context. Gold remains evaluator-only, outside the installed wheel.

The validator checks the unchanged source oracle and all non-text query metadata, complete
prior-question lineage, exact author/label/question bindings and frozen runtime versions.
NFKC/casefold/whitespace normalized replay and duplicate wording are rejected. The retained
lexical audit found zero normalized replays and maximum prior token Jaccard 0.471. This lexical
check is advisory; shared semantic/template ancestry still limits independence.

```bash
.venv/bin/python -m tools.run_g2_pilot --run-live \
  --python /tmp/pil-original-env/bin/python \
  --dataset evals/procurement_corpus/fresh-language-v2 \
  --manifest evals/operational_agents/fresh-language-v2.json \
  --database /tmp/pil-fresh-language-v2.db \
  --output artifacts/fresh-language/v1/first-run.json
```

Fresh database/output paths are required. The original default invocation remains a
historical development regression. New selected dataset paths propagate through frozen
loading, report hashes and the real installed structured HTTP baseline. All 48 gold/source
checks must pass before inference. Reports retain pass/fail/unknown/not_applicable by
project/category/split, actual journal counts, tool starts, latency, saved identities and
exact recovery/repeated approval. Missing terminal evidence blocks acceptance.

## Independent review

Review at `c5a948c761524ecf2622f236ecb19581d1107e0f` found one Important provenance gap:
query dates/categories could change while preserving author hashes and category totals.
Four mutations plus the real evaluator entry point reproduced it RED. The author correction
requires complete original query metadata equality except question text, rejecting category,
date, item and extra action fields before composition/inference. Sixty focused tests pass.
No Critical/minor findings. Subsequent dataset/results/full/installed/CI verification is an
explicit author fresh pass, not a second independent review.

The roadmap advisory [37189328482](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/37189328482)
failed Gemini daily-quota 429; no usable advisory. Live Project planning was deliberately reviewed.
Deployment, comprehensive browser accessibility, full G2/release and expansion remain distinct gates.

## Frozen executed results

Executed at `d6b7d1d9190ce39b061026904090655a1b6d87a0`, with unchanged installed
application/model/prompt/tool/corpus bindings. [Compact results](fresh-language-results.json).

| Group | Passed | Failed | Unknown |
|---|---|---|---|
| Root development | 24 | 0 | 0 |
| Independent validation | 11 | 1 | 0 |
| Independent test | 12 | 0 | 0 |
| All | 47 | 1 | 0 |

Installed structured HTTP passed 48/48 gold cases and 464 original quantity/authority source checks.
Journals reconcile 48 unique terminal inference attempts, 54 tool starts and 27 exact saved results.
All 27 accepted investigations matched complete deterministic facts, recovered in a new CLI process,
rejected altered digests and acknowledged the same result after repeated approval. All 20 expected
abstentions passed and exercised no tool/save authority. No false factual answer was observed
among accepted cases; this does not establish a general safety/accuracy rate.

The retained miss is `cinder-before-boundary`: “Set the review cutoff to
2026-08-31T23:59:59+00:00 and examine the governing requirement for NIC-C1.”
Expected read-only investigate; actual unsupported/unsupported. The explicit date matches caller
cutoff, so setting the review parameter here grants no procurement write authority. The model
misinterpreted a valid query; it invoked no tools and saved nothing. This is a failed target,
not a false confident answer. No expectation edit, prompt tuning or retry occurred.

The bounded live evaluation is **not_ready** with one failure. The independent language cohort
is 23/24, not 24/24; the original source/project data is not fresh. Prior 41/48 pilot and 46/48 development
results remain immutable and are not a controlled paired comparison with this new wording cohort.
Any next interpretation development must retire this cohort as inspected language data and use
a new independently authored evaluation for later claims. Keep explicit caller cutoffs in the
live demo and present abstention honestly. Full G2/release/expansion remain gated.

Final corrected deterministic suite: 666 passed, 10 explicit opt-in skips,88.15% coverage and ratchet,
strict static/types/architecture. Focused 60 tests pass. Runtime resources/packaging/challenge oracles
were unchanged; the clean installed wheel’s versions and actual HTTP/CLI paths were verified.
No new shipped semantic defect or model/algorithm swap is claimed.
