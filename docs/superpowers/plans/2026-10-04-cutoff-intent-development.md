# Cutoff intent development execution increment

> Native execution of approved corpus Task5B/5C; use superpowers:executing-plans.

Primary #53/M8, Part of #66/#67/#68/#70/#71/#72. Stack on draft #186, no merge/deploy.
Spec: docs/superpowers/specs/2026-10-03-procurement-demo-corpus-design.md and ADR-032.
Bounded design approved by continuation: distinguish restating a matching human-selected review
cutoff from procurement mutations. Different dates/projects, unresolved relative dates and ambiguous
items still clarify. Save requires existing exact human approval; no policy or port changes.

## Global constraints

Use already-loaded local Qwen3.6, unchanged schema/transport/budgets, no reload/paid provider/traces.
No corpus expansion. Retire fresh-language-v2 from further holdout claims before tuning; its first
47/48 report remains immutable. New measurements use development labels. Freeze all controls first.
One attempt per case per configuration/run; no retry. Generic prompt examples cannot contain source
identifiers, test case IDs or gold. Model input remains question/catalog/project/caller cutoff only.

## Task 1: freeze development controls and reproduce the miss

- [ ] Freeze evals/operational_agents/cutoff-development-v1.json: unchanged prior20 controls plus
  eight matching/conflicting date, foreign project, source mutation, direct approval, mixed injected
  review and alias controls. Record overlap with inspected fresh evaluation.
- [ ] Allow the existing opt-in installed CLI test to select PIL_INTENT_MANIFEST (default unchanged),
  use selected manifest hash and its complete denominator. No shipped runtime changes.
- [ ] Freeze a v1 development-regression interpretation manifest referencing the unchanged48new
  question dataset. Keep original fresh v2 manifests/results byte-identical.
- [ ] Commit before calls; installed old runtime versions must equal checkout. Run the28 controls
  once and retain all outcomes. Confirm actual cutoff miss RED before any prompt change.
- [ ] Task verification audits immutable baseline report/journals; a failing product target is
  evidence, not permission to retry or alter expected labels.

## Task 2: clarify the existing prompt and measure the candidate

- [ ] Change only adapter PROMPT: review-cutoff selection is request metadata, not a procurement
  write; matching explicit date can investigate after all scope/time/literal-item checks. Different
  dates clarify; unsupported write-only/approval commands remain unsupported. Generic contrasting
  examples, no dataset IDs/gold. This is a measured prompt experiment, not deterministic NLP policy.
- [ ] Build/install a clean optional wheel; inspect runtime versions before inference.
- [ ] Run same28controls once with candidate; retain unknown/fail outcomes and zero saved results.
  Run48inspected-language development regression through installed HTTP/CLI/recovery/exact save once.
- [ ] Run make check, package smoke, C001-C017 current/known-bad checks. Freeze runtime before checks.
- [ ] Record baseline/candidate outcomes, source correctness, journal counts/timing/version/hash and
  overlapping repeated measurements. Reject any unsafe date/scope/save result; retain safe misses.

## Task 3: independent review and branch closeout

- [ ] One fresh-context whole-branch review of code/tests/reports; Important/Critical findings get
  one author RED/GREEN correction pass and full checks, no second reviewer; minors deferred.
- [ ] Update ADR-032 clarification, handoff/milestone/README and #53/#72 as materially needed. Latest
  head semantic evidence and PR contract distinguish development reliability from heldout quality.
- [ ] Publish stacked draft, verify exact-head deterministic CI and planning audit; keep broader
  Issues open, no merge/deploy/expansion. Archive only this execution workspace.

## Review Focus

Matching vs different explicit date; source mutation vs query metadata; relative/foreign/alias/multiple
controls; injected save stays awaiting review; installed bytes and prompt-bound recovery versions;
retired holdout labels not silently reused; all calls/saves/unknown denominators reconciled; unchanged
numeric gold/source policies and original showcase regressions. No new shipped semantic defect is
claimed for an unmerged prompt experiment; C001-C017 remain applicable.
