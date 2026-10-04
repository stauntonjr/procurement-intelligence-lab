# G2 evidence consolidation implementation plan

> For agentic workers: use superpowers:executing-plans for approved native continuation.

Goal: produce a replayable, hash-bound #72/M9 acceptance dossier from retained evidence, including
an actually measured installed deterministic baseline. Architecture: evaluator-only reader/compiler;
unchanged application and existing public inspector own facts. No new runtime policy or subsystem.
Spec: approved 2026-10-03-procurement-demo-corpus-design.md Gold evidence/evaluation and parent
2026-10-03-procurement-demo-corpus.md Task5A/5C. Stack on draft #189. Governing #53/#67/#68/#70/#71/#72/#73/#74.
Tech: stdlib JSON/hash/statistics/subprocess, existing installed_inspector and corpus evaluator.

## Global constraints

Read frozen reports; no new inference, tuning, retries, model reload, paid calls, trace export,
source/gold changes, corpus expansion, merge or deployment. Controls stay inspected development
and retain all failures. Nine original trials are three repetitions of three correlated fixtures;
48 fresh-language queries include only24 independently authored questions over known sources.
Do not pool populations into an aggregate accuracy/latency or imply causal baseline comparison.
Controlled protocol counters/usage remain separate from real model observations. Missing reports,
rows, audit records or metrics remain unknown; contradictory bindings fail. Unavailable cost null.
Baseline timing is one sequential public HTTP run in a fresh installed process; OS/cache warm/cold
state unmeasured. Report investigator roundtrip separately from source lookup and model transport.
Broader release/browser/accessibility/deployment/main-integration gates stay unmeasured, blocking
full G2/B2 readiness even if the bounded installed suite has positive evidence.

## Task 1: offline compiler and public CLI regressions

Files: tools/g2_evidence.py (pure report checks/metrics), tools/consolidate_g2_evidence.py
(hash/path reader, baseline/public CLI), existing tools/evaluate_procurement_corpus.py
(optional fetch callback; default behavior unchanged), tests/unit/test_g2_evidence.py,
tests/integration/test_g2_evidence_cli.py. Manifest/report interfaces below feed Task2.
- [ ] RED: missing/duplicate/foreign rows or causal evidence cannot pass; changed hashes and
  versions fail; controlled attempts cannot become real metrics; historical control failures
  remain visible; no reports cannot produce zero calls or readiness; negative/nonfinite timing
  fails, absent timing remains null. Exercise actual CLI, existing output refusal and no inference.
- [ ] Implement closed source roles: fresh_language, original_browser, adversarial,
  baseline_controls, candidate_controls, deterministic_baseline. Frozen manifest binds role,
  relative report path/SHA256, expected row IDs, versions and historical/gating use.
  compile_report(role, report, spec) returns evidence status, observed outcome counts,
  actual counts and separate timing/usage. consolidate(manifest, artifact_root) keeps every role.
  Original factual/source/run/save checks reference the already pinned original scenario manifest;
  adversarial causal evidence reuses current audit_evidence; fresh attempts reconcile audit rows.
- [ ] Run focused public/unit/static/type checks; commit compiler. Whole make check runs at the
  final reviewed revision in Task2, before publication, so review fixes receive one current full check.

## Task 2: installed baseline, frozen dossier and whole-branch review

Produces evals/operational_agents/g2-evidence-v1.json and docs/project/g2-acceptance-results.json;
raw baseline/dossier/logs retained in artifacts/g2-evidence/v1/. Consumes Task1 compiler.
- [ ] Verify reused clean wheel100Python byte/version parity; measure48 deterministic requests
  and464source checks once through installed HTTP, zero model calls. Freeze raw baseline/report
  hashes before consolidation. Invoke actual CLI with fresh output; inspect all denominators,
  costs/nulls/version/causal bindings and timing population labels. No inference retry or rerun.
- [ ] One independent whole-branch review including final raw artifacts; single author RED/GREEN
  fix pass for Critical/Important, no second review. Run make check at that latest revision to PASS
  before publication. Later documentation exactHEAD author fresh pass.

## Task 3: durable acceptance dossier and draft publication

Files: docs/project/g2-acceptance-dossier.md, README/handoff/milestone map, completed snapshot
of prior adversarial publication checklist. Consumes verified Task2 output, not new inference.
- [ ] Document precise passing installed gates, historical misses, latency/cost boundaries and
  ordered remaining browser/release work. Keep broad Issues open/InProgress. Publish stacked draft,
  revision-bound semantic evidence, postwrite planning audit and all10required exact-head CI.
  Archive only this plan's scratch after completion. No merge/deployment/expansion.

## Review focus

1. Missing or contradictory historical inputs cannot turn into success or zero measured calls.
2. Foreign/partial causal records and double saved results cannot pass through a report flag.
3. Fake provider usage, repetitions, development controls and independent language remain distinct.
4. Original source fixture differences are bound explicitly; application/prompt drift cannot pass.
5. Timing scopes are honest, unknown metrics/cost remain null, and global release is not inferred
   from local evidence. No source/raw reasoning/token credential export or operational authority.
