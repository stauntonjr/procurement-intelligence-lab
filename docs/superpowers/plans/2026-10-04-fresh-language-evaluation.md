# Fresh language evaluation execution increment

Approved parent: 2026-10-03-procurement-demo-corpus.md Task5A/5C; spec's retired-test rule.
Native execution; primary #72/M9, part of #53/#70/#71. Stack on draft #185; no merge/deploy.
Purpose: measure unseen wording against unchanged runtime and known synthetic source scenarios.
Model: already loaded local Qwen3.6, one attempt per48cases, no reload/providers/uploads/tuning.
This is question-language holdout only, not new project/data independence. All old cases remain
inspected development artifacts. No corpus expansion or fullG2 acceptance inferred.

## Task 1: frozen cohort integrity and manifest contract

Inputs: existing4project/48case oracle metadata, gold/qrels unchanged; source/runtime versions pinned
before authoring. Development24 questions are root-authored; validation/test24 are independently
authored in the single fresh-context review seat, without seeing old questions/model outputs/prompt.
The evaluator can see gold; application/model cannot. No copied validation/test phrasings.

- [ ] Add RED tests for v2 manifest: strict metadata and hash/author/case binding, changed runtime,
  duplicate/missing author rows, project/split mismatches, old wording replay, unsupported provenance.
- [ ] Implement evaluator-only tools/fresh_g2_cohort.py: validate_fresh(dataset,manifest,versions=None).
  Load/query/gold/role validation remains existing load_dataset/load_pilot. Bind24heldout authored
  rows and their question hashes/expectations to new queries, corpus+old query hashes and frozen
  run versions. Normalize NFKC/casefold/whitespace for exact wording replay and reject duplicates.
  Root development questions are recorded separately; no claim of independently authored development.
- [ ] GREEN new integrity plus existing pilot scoring tests, commit.

## Task 2: actual evaluator caller selects frozen inputs

- [ ] RED actual main CLI tests for --dataset/--manifest selected paths, historical default behavior,
  changed runtime refusal before model, startup failures retaining48unknowns, no overwrite.
- [ ] Generalize run_g2_pilot.py selection consistently through load/hash/structured evaluation.
  v1 stays development_regression; validatedv2 reports fresh_language_holdout and explicit reuse limits.
  No source/prompt/model/application changes. Golden HTTP48/48 gates any live call. No retries.
- [ ] GREEN selected public caller, full make check; verify current clean installed artifact versions.
  Record protocol/authoring metadata and root development texts, commit before review.

## Task 3: independent authoring, single frozen execution and closeout

- [ ] One read-only whole-branch review using code-reviewer.md; same independent reviewer authors
  validation/test24 texts/closed interpretation labels from source/request metadata and contract,
  not old query text/model/prompt output. Return authored records as a review artifact. Root checks
  schema/gold/source intent and overlap; any impossible ambiguity is corrected before inference only.
  Important/Critical code findings get one author RED/GREEN fix pass; minors deferred.
- [ ] Materialize new evaluator dataset with existing gold/qrels and changed queries only; preserve
  old split/project/category/scenario lineage and quantify lexical similarity. Author labels never
  enter model input. Freeze manifest/data/review/source/runtime hashes in commit before calls.
- [ ] Run actual clean installed48queryHTTP baseline plus48 local Qwen CLI interpretations/review/
  recovery/ledger checks using freshDB/output. Retain all fail/unknown outcomes; no tuning/retry.
  Report dev24 and unseen validation12/test12 separately, not broad quality or olddata independence.
- [ ] Publish versions/results, handoff/milestone/Issue updates and latest-revision semantic evidence;
  push stacked draft and verify exact-headCI. Keep broader Issues open and expansion gated.

## Review Focus

No old questions relabeled heldout; exact/normalized overlap and shared source ancestry; author
records/labels/hash/runtime binding; schema and numeric oracles unchanged; v1 defaults unchanged;
all selected paths used by real caller; report/journal/unknown denominator reconciliation; no gold
in model inputs/runtime package; one attempt per case; source-selected original workflow preserved.

## Recorded execution ruling

The single required independent review is before live execution so its fresh-context reviewer can
also author the protected question cohort. Subsequent results/data/closeout get an author fresh
pass, explicitly not a second independent review. Cost if wrong: unreviewed report/data defects.
Reuse clean primary checkout on a new stacked branch. Cost if wrong: checkout coordination.
