# G2 pilot evaluation implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; one independent whole-branch review.

**Goal:** Execute the frozen four-project pilot through installed deterministic HTTP and local Qwen CLI, retaining truthful per-layer outcomes.
**Architecture:** Evaluator-only files consume existing public callers and read the application ledger for independent trajectory/save checks. No runtime/model/prompt changes, no new authority or dependencies.
**Tech Stack:** Python stdlib, existing pytest, optional installed workflow wheel and currently loaded Qwen.
**Spec:** [Approved corpus design](../specs/2026-10-03-procurement-demo-corpus-design.md), Task 5A/5C of [approved plan](2026-10-03-procurement-demo-corpus.md), ADR-032, Issue #72 (M9).

## Global constraints

Freeze original 48 query texts, project/as-of inputs and interpretation expectations before inference. Send only question and caller-selected project/date to the application; gold/case IDs remain evaluator-only. Identifier-free paraphrases require clarification under the existing literal contract; unsupported purchase action requires unsupported. Preserve separate structured gold and natural-language outcomes. One fresh live run per example, no retry or prompt tuning. Retain fail/unknown and category/project/split denominators. Shared generator ancestry precludes a blind quality claim. Browser/deployment, full adversarial G2 gates and expansion stay open.

## Review focus

- Omitted or duplicate queries must not inflate acceptance: Task 1.
- Correct quantities without original supporting sources must fail: Task 2.
- Clarification cannot hide an unexpected investigation or save: Task 2.
- Fixture, foreign or incomplete trajectories must not count as live success: Task 2.
- Timeouts must retain partial records and unknown usage, without model retry: Task 2.

## Task 1: freeze interpretation and scoring

Files: `evals/operational_agents/g2-pilot-v1.json`, `tools/g2_pilot_scoring.py`, `tests/unit/test_g2_pilot_scoring.py`.
Interface: load_pilot(dataset, manifest) validates original query hash, exactly 48 unique IDs and closed dispositions; score_intent(case, outcome) and summarize reports explicit outcome counts by project/category/split.
- [ ] Write missing-module tests for frozen counts, wrong item/date, false-confident output, omitted/duplicate results and invalid expectation.
- [ ] Run focused tests: expected missing-module failure.
- [ ] Implement minimal scorer and freeze all expectations before live execution.
- [ ] Run tests to PASS; record commands and commit.

## Task 2: run installed public pilot

Files: `tools/run_g2_pilot.py`, `tests/unit/test_g2_pilot_runner.py`.
Interface: explicit `--run-live --python PATH --database FRESH_PATH --output FRESH_PATH`. Installed HTTP first scores all 48 structured cases and every source against existing gold. Live CLI submits original texts without oracle item/action; accepted requests compare complete baseline facts, recover in new process, reject altered approval, approve/repeat save. Durable events and saved count independently bind each run/scope/version. Retain report after every phase/example including errors; no inference retry.
- [ ] Add failure tests for source errors, partial/foreign/fixture records and CLI timeout retention; run RED.
- [ ] Implement runner; run focused tests GREEN.
- [ ] Execute one frozen actual Qwen pilot from clean installed wheel; preserve every outcome without tuning. Report process, model and trajectory latency separately.
- [ ] Run make check and affected challenge validation; no package/runtime resources changed, reuse verified wheel with identical application digest.

## Task 3: review and publish evidence

Files: `docs/project/g2-pilot-evaluation.md`, compact `docs/project/g2-pilot-results.json`, handoff/milestone map, revision-bound semantic evidence and draft PR.
- [ ] Record results, earlier development history, limits and next acceptance work; review frozen dataset ancestry honestly.
- [ ] Independent latest branch review; one author fix pass for Important/Critical with RED/GREEN checks.
- [ ] Validate latest semantic JSON and required CI; update #72 evidence/Project deliberately, keep broader gates open.
