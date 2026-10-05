# Serial review workflow checkpoint slice

Spec: `docs/superpowers/specs/2026-10-03-procurement-demo-corpus-design.md`, Task 5B
of the approved corpus plan. Primary M5 / #53; part of #68 and #70.

Implement the optional LangGraph adapter behind `AgentWorkflowRuntime`, using typed
fixture requests and the existing audited tools and exact-brief service. No inference or
natural-language quality claim. Model interpretation, browser controls and live acceptance
remain subsequent gates.

## Task 1: durable workflow and public caller

1. Write failing contract and real-process CLI tests for pause, owned resume, reject,
   configuration drift, wrong digest, duplicate save and crash after durable save.
2. Pin an optional workflow extra, keep the base wheel dependency-free, and implement
   explicit partial graph updates with application-owned approval and result records.
3. Serialize invocations with a bounded local lock; reject checkpoint forks and unauthorized
   loading. Runtime context and permissions are never checkpoint fields.
4. Bound graph steps and check an invocation deadline between nodes. Do not claim hard
   cancellation of synchronous tools. One read attempt; no unclassified retry.
5. Exercise the public CLI and base/extra clean-wheel paths, run `make check`, challenges,
   and a fresh independent whole-slice review; reproduce important findings before fixes.
6. Record revision-bound evidence, update handoff/planning and publish a stacked PR.

Expected: focused tests, full checks, clean-artifact probes and challenges pass. #53/#68
remain open. No merge/deployment or model invocation is implied.

## Review Focus

Deliberately check checkpoint payload tampering, absent checkpoints, orphan durable drafts,
crash windows before/after receipt/save, concurrent resume, changed evidence, expired
approval, dependency-free import, unauthorized pre-deserialization access, public field
allowlisting and invocation deadline limitations.
