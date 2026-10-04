# Fresh language v3 evaluation of the cutoff candidate

Primary #72/M9, part of #53/#70/#71. `codex/fresh-language-v3-evaluation` is stacked on
unmerged draft #187. This executes the approved corpus plan Task5A/5C retired-test rule:
new wording, unchanged candidate runtime, sources and numerical oracles.

## Frozen contract

The [48 questions](../../evals/procurement_corpus/fresh-language-v3/queries.json) keep every
original non-text request, project, split, category and execution-layer field. Gold and qrels
are byte-for-byte original. Atlas/Borealis contain 24 root-authored development questions;
Cinder/Delta contain 12 validation and 12 test questions authored in a fresh independent context.
The [author record](../../evals/procurement_corpus/fresh-language-v3/independent-language-author.json)
was saved before exposure to old questions, results or runtime prompt, SHA256
`d8565e15de68c55311aab21255e59186371ae30ad4239b3cbb4e7f0dec7b9339`. It was not edited after exposure.

The [version3 interpretation manifest](../../evals/operational_agents/fresh-language-v3.json)
requires all seven inspected question files, including the retired v2 language cohort and cutoff
controls. Historical version2 retains its five-file lineage. Normalized NFKC/casefold/whitespace
replay and duplicates reject; missing/changed lineage, author, source, query metadata or runtime
binding refuse before inference. Advisory prior token Jaccard maximum is 0.400, with zero normalized
replays or duplicates. This is new language over known correlated synthetic source/scenario families,
not new-source/project independence, a blind benchmark, statistical sufficiency or causal prompt proof.

Runtime was frozen before authoring at `f583e97d566d2e0d86b531afae6991fa27796386`:
loaded `nvidia/Qwen3.6-35B-A3B-NVFP4`, candidate prompt `a1988e677c510162e5e582d2cf5c49a3fdd12655691ce5bd2008424998179592`,
application `sha256:afe3ae789743d40c56de8f5cf51c73334f865217e78a92184994633043a55146` and
source manifest `a92add68a76dca7bf0818bc073b0d8f127c0a6b28544c22f62b90d143fa4bd64`.
Dependencies/tool schema and full bindings are in the manifest. No reload, tuning, retry, provider
change, paid call, trace upload, corpus expansion, merge or deployment.

The clean installed wheel from the cutoff experiment was reused. Its SHA256 is
`c6abc43be4f5d0e5fbe4113bb07914ee9d57c152d0998d5777ad844db7a7051e`; all 100 runtime Python
files match checkout, wheel and installation, and composition versions match the freeze. Runtime and
package bytes are unchanged; this evaluator increment does not claim a new release/package result.

## Actual caller and evidence

```bash
.venv/bin/python -m tools.run_g2_pilot --run-live \
  --python /tmp/pil-cutoff-env/bin/python \
  --dataset evals/procurement_corpus/fresh-language-v3 \
  --manifest evals/operational_agents/fresh-language-v3.json \
  --database /tmp/pil-fresh-language-v3.db \
  --output artifacts/fresh-language-v3/v1/first-run.json
```

Fresh output/database paths are required; do not overwrite or rerun this cohort for a quality claim.
The installed structured HTTP/source oracle must pass before model calls. The installed CLI receives
only question, project and selected cutoff, never gold, case labels or structured oracle item/action.
Each question has one attempt and owned version-bound run. Accepted investigations compare complete
facts, recover in a new CLI process, reject altered digests and acknowledge repeated exact approval
with one saved result. Abstentions must have no tools or save. Journal/model/tool/save counts and all
fail/unknown outcomes are retained.

Full artifact directory: `artifacts/fresh-language-v3/v1/` (local, ignored): runtime/cohort freeze,
author brief, lexical audit, installed parity, independent review, deterministic log and first-run
report. Durable compact results are recorded separately. Once this cohort is used for development,
retire it as inspected language data before tuning and obtain new evaluation wording for later claims.

## Review and completion boundary

The same independent author seat reviewed evaluator `136c61eeb2c0ad09919ff8526b9213acbb710833`
after freezing its questions. No Critical/Important/Minor findings; independently executed 69 focused
checks passed. Review SHA256 `eb59be39a93ed2421a17688b5ead88ad44ba9f310d9f151b3b59ac5a84863569`.
Later materialized data, live outcomes, compact results and final revision receive an explicit author
fresh pass, not a second independent review. The author checks complete hashes, original metadata,
intent/date consistency, journal/save reconciliation, claimed outcomes and remaining acceptance gates.

Deterministic suite: 675 passed, 10 explicit live/browser opt-in skips, 88.15% coverage, coverage
ratchet and static/type/architecture checks passed. Nine new provenance/actual-main regressions
failed before implementation and passed afterward. No runtime semantic defect, model/algorithm swap,
new adapter or package change is claimed. Prior manifests, datasets and results remain immutable.

Full G2/release, comprehensive browser accessibility, deployment and corpus expansion remain separate
open gates; keep #72 and related Issues open. The prior roadmap advisory failed Gemini daily-quota
429 and produced no usable report; live Project planning was deliberately reviewed for this bounded
continuation, without claiming a successful advisory or a merge wave.

## Frozen executed result

Executed at `dd77a3be8727f2d8540e60794df05b72d00495f5`, using the unchanged frozen candidate
and clean installed artifact. [Durable compact outcomes](fresh-language-v3-results.json).
First report SHA256: `40b5e4b46c7604a88a6827dc65f821ab6f568af11990c9e1009025e64c575f41`.

| Group | Passed | Failed | Unknown |
|---|---|---|---|
| Root development | 24 | 0 | 0 |
| Independent validation | 12 | 0 | 0 |
| Independent test | 12 | 0 | 0 |
| All | 48 | 0 | 0 |

Installed deterministic HTTP passed 48/48 gold cases and 464 original source checks before
inference. The author audit reread SQLite journals: 48 unique terminal model calls,
56 tool starts, 28 exact saved results and unchanged frozen hashes. All 28 accepted investigations
matched complete deterministic facts, recovered in a new CLI process, rejected altered digests and
acknowledged repeated exact approval with one save. All 20 expected clarification/unsupported
questions passed with zero tools and zero saves. No tuning, expectation edit or retry occurred.

The bounded pilot is **bounded_pilot_passed**. Independently authored new language is 24/24;
this is not 48 independent held-out questions, a causal comparison with v2, broad language accuracy,
or a fresh source dataset. The historical cutoff control run still retains two supported-request
abstentions and is not overwritten by this result. Temperature0 is not deterministic NLP.
Full G2/release readiness remains **not_ready** pending the other acceptance gates.

Next: consolidate the release-blocking G2 adversarial matrix against the real installed application
and existing original/corpus scenarios, with explicit source, malformed/scope/tool/approval/restart
and repeated-save evidence. Keep browser/accessibility and deployment gates distinct. Address the
small-dataset concern through the approved B2 source-diversity expansion only after those gates;
new wording alone has not expanded the four projects, 24 workbooks or 960 source rows.
