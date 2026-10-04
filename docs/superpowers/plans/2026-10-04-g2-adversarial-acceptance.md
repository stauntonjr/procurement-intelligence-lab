# Installed G2 adversarial acceptance implementation plan

> For agentic workers: use superpowers:executing-plans for approved native continuation.

Goal: retain release-blocking failure-boundary evidence from the actual installed HTTP reviewer.
Architecture: evaluator-only launcher injects faults behind existing ports/clock/save boundary;
unchanged application owns authentication, scope, journals, tools, exact review and persistence.
Spec: [approved design](../specs/2026-10-03-procurement-demo-corpus-design.md) release gates and parent plan Task5A/5C;
ADR-029/030/031/032, primary #72/M9; part of #53/#66/#67/#68/#70/#71/#74. Stack on draft188.
Tech: stdlib subprocess/HTTP/SQLite; existing clean workflow wheel and loaded local Qwen3.6.

## Global constraints

No runtime/prompt/source/gold/package changes, model reload, paid provider, trace export, expansion,
merge or deployment. Existing evidence remains immutable. Freeze harness/runtime/input hashes before
execution. Five real Qwen calls maximum, one per live case, no inference retry. Controlled HTTP model
responses are protocol fault injection, never real Qwen quality/latency/token aggregates. Dynamic
controlled endpoints have their own actual runtime bindings. All failures/unknowns retained.
Nine cases: request_guards, malformed_model, foreign_model_scope, transport_failure (controlled);
unsupported, tool_timeout, expired_approval, changed_snapshot, review_crash_scope (real Qwen with
explicit evaluator mechanical faults). All accepted seed briefs must match installed deterministic
HTTP facts and resolve their source IDs. The crash case includes awaiting-review process restart,
foreign project read/recover/review refusal, checkpoint/approved extra-field refusal, altered digest,
actual exit86 after durable save, fresh-process exact replay and one saved result.

## Task 1: evaluator and deterministic public proof

Files: tools/g2_adversarial_server.py (installed application launcher/faults),
tools/run_g2_adversarial.py (closed cases/HTTP caller/report/journal audit),
tests/unit/test_g2_adversarial_scoring.py, tests/integration/test_g2_adversarial.py.
Interfaces: server child announces port and actual versions; running(...) owns process cleanup;
run_case(id, python, directory, endpoint, kind) returns one retained observation;
summarize(records, protocol_only=False) preserves nine closed denominators and distinct call kinds.
- [x] RED: omitted/duplicate/unknown records cannot pass; controlled calls never count as real;
  injected workflow failure can pass the guard while retaining its actual failed status.
- [x] Implement protocol-only CLI (four controls, five explicit N/A, no live acceptance claim).
  Public integration runs real HTTP/child processes against controlled protocol responses;
  exercise timeout/expiry/snapshot/crash cases with valid controlled interpretation as well.
- [x] Run focused tests and make check; commit evaluator. Single fresh independent evaluator
  review before live calls; one RED/GREEN fix pass for Critical/Important, defer minors.

## Task 2: frozen installed execution

Consumes Task1 runner; produces immutable report/freeze/parity/observations consumed by Task3.
- [x] Verify reused cutoff wheel100Python byte parity and normal runtime versions equal current
  checkout; record wheel/hash and actual per-case injected versions/launcher hashes.
- [x] Execute actual CLI once with clean installed Python, fresh workspace/output. Require all
  nine case observations, actual terminal journals, expected tool failures, no unauthorized
  reads/briefs/saves, stale approvals rejected and exact crash-save identity preserved.
  Independently reread run/receipt ownership, one approval binding and all durable saved records.
- [x] Author fresh pass on later data/results, not a second independent review. Report bounded
  adversarial gate separately from historical model-control misses and global G2/release status.

## Task 3: durable evidence and publication

Consumes verified Task2 artifacts/counts; produces docs/project/g2-adversarial-acceptance.md and
compact outcomes, handoff/milestone/README and exact-head semantic evidence.
- [ ] Publish stacked draft, keep Issues open and Project status accurate; audit planning after
  writes. Verify all10required exact-head CI checks, then archive only this execution workspace.

## Review Focus

No auth/scope failure may create a journal or read a foreign checkpoint; controlled endpoint errors
are not real model quality; actual failed attempts remain visible even if safety guard passes;
missing/partial/crash evidence cannot turn into success; tool/clock/save injections are explicit
and separately hash-bound; crash proof requires exit86 plus same one durable result after restart;
no raw prompts/provider reasoning/token credentials in retained public payloads. Full deployment,
comprehensive accessibility, broader release acceptance and B2 expansion remain separate gates.
