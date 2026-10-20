# Document Review Lineage Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, TDD and one fresh-context whole-branch review.

**Goal:** Durable evidence-bound document-value correction/review lineage without rewriting source facts.
**Architecture:** Core frozen records/Protocol; domain validator; explicit application authorization;
Postgres additive journal and separate human CLI, composed in bootstrap.
**Tech Stack:** stdlib dataclasses/Decimal, existing psycopg3/storage extra and typed DAG codec.
**Spec:** docs/superpowers/specs/2026-10-20-document-review-lineage-design.md

## Global Constraints

Archive schema1, old BOM/demo/brief behavior and original facts remain compatible. Only document_value;
no entity/operational review, governing policy, unit change, automatic recomputation or deployment.
Every input/decision has typed value, exact scope/time/evidence and stable retry/conflict semantics.
No new challenge manifest is required: this introduces a new capability, not a shipped defect.

## Review Focus

- Changed request content or altered task digest must never reuse a successful decision.
- Null/zero/negative/fractional/type distinctions and original unit/evidence survive restart.
- Runtime agents or foreign/version scopes must never acquire review authority.
- Future decisions must not leak into historical pending views; no backdated approval.
- Failed writes/corrupt source membership cannot leave or report a partial correction.

### Task1: Neutral contract and explicit application review service

Files: platform/semantics/document_reviews.py, ports/document_reviews.py,
application/document_reviews.py, domains/procurement/document_reviews.py; unit tests.
Consumes archived SourceAssertion and RequestContext; produces ReviewProposal/Task/DecisionCommand/
Decision/History, Journal Protocol and application propose/decide/show/history with injected clock,
archive, journal and proposal validator.
- [ ] Write boundary tests for missing/foreign/unsupported/digest/time/value/authority cases.
- [ ] Run focused unit tests and observe missing feature failures, then implement minimal contract.
- [ ] Verify positive and negative cases and exact typed task digest/identity stability.

### Task2: Atomic Postgres journal and explicit composition

Files: adapters/postgres_document_reviews.py, bootstrap.py; contract tests.
Consumes Task1 journal contract and existing archive1/codec; produces initialized additive journal.
- [ ] Write real isolated DB tests for init/retry/concurrency/conflict/rollback/as-of/SQL guards/corruption.
- [ ] Observe RED; implement fixed schema, transaction mechanics and strict retained-data/source validation.
- [ ] Verify existing archive reads/bytes unchanged and all targeted contracts GREEN.

### Task3: Public human CLI and clean artifact acceptance

Files: interfaces/document_review.py, tools/archive_package_probe.py, docs/handoff/milestone/README;
actual subprocess and in-process parser contracts.
- [ ] Add actual propose -> restart/show -> exact approve/reject -> historical reads and denial tests.
- [ ] Observe RED; implement strict request JSON and trusted human configuration, typed failures.
- [ ] Extend installed storage probe and absent-driver checks; document exact contract and acceptance.

### Task4: Seal, qualify, review and deliver

- [ ] Seal code, run make check/ratchet, clean package, all30 challenge/mutations and source conformance.
- [ ] Independent latest-head architecture/semantic review; resolve concrete findings with regressions.
- [ ] Embed validated same-head JSON in PR; every required deterministic check green before merge.
- [ ] Verify merged main/tree/caller; close216 only, ProjectDone, broader13/37/41 stayopen/InProgress;
  postmerge planning audit and advisory roadmap evidence. Preserve shared workloads and old worktrees.
