# Project handoff

## Purpose and use

This page is a concise orientation index for a fresh human or development agent. It explains where the current state is recorded and what to read first; it is not a transcript, decision log, or duplicate architecture specification.

Start with [AGENTS.md](../../AGENTS.md), then read the relevant [GitHub Issue](https://github.com/stauntonjr/procurement-intelligence-lab/issues), linked ADRs, and the authoritative documents below before changing the repository.

## Current milestone and status

- **M7 — Append-only persistence and temporal/as-of state:** in progress. See the [canonical milestone map](../development/milestone-map.md), [Issue #91](https://github.com/stauntonjr/procurement-intelligence-lab/issues/91), and [ADR-015](../adr/ADR-015.md).
- **M8 — Retrieval projections and review UI:** planned.
- **M9 — Guarded actions, product signals, and integrated evaluation:** planned.
- The initial M0–M6 evidence-first vertical slice is complete on `main`; the [root README](../../README.md) records the current product boundary and runnable entry points.

## Current architecture

The system preserves evidence from synthetic/semi-structured procurement documents through structured mapping, source assertions, entity mentions, resolution decisions, canonicalized assertions, reconciliation, operational state, and derived intelligence. Core semantics remain framework-independent; adapters own external mechanics. Postgres is the intended canonical store, while lexical, vector, and graph systems are replaceable projections. Deterministic services compute and enforce policy; AI-assisted interfaces explain and route work. See [architecture overview](../architecture/overview.md), [semantic model](../domain/semantic-model.md), and [architecture tradeoffs](../architecture.md).

## Recently completed

- M0–M4 repository, evidence, claims, and constrained chat foundations.
- M5 local HTTP chat/evidence inspector; see [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82).
- M6 durable identifiers, source viewer, and review context; see [PRs #86, #88, and #90](https://github.com/stauntonjr/procurement-intelligence-lab/pull/90).
- Initial procurement query contracts and public-dataset planning; see [draft PR #76](https://github.com/stauntonjr/procurement-intelligence-lab/pull/76).

## Active work and PRs

- [PR #94](https://github.com/stauntonjr/procurement-intelligence-lab/pull/94) implements the M7.1 anomaly taxonomy and provenance boundary.
- [PR #95](https://github.com/stauntonjr/procurement-intelligence-lab/pull/95) fixes the related anomaly-test constructor failure.
- [PR #93](https://github.com/stauntonjr/procurement-intelligence-lab/pull/93) adds layered PR review governance.
- [PR #84](https://github.com/stauntonjr/procurement-intelligence-lab/pull/84) documents agent-framework evaluation strategy.
- M6 follow-on work is tracked by [Issues #85, #87, and #89](https://github.com/stauntonjr/procurement-intelligence-lab/issues/89).

## Settled decisions

- Preserve provenance and source assertions; do not turn extraction or similarity into truth.
- Keep domain semantics framework- and database-independent, with explicit ports, adapters, dependency injection, and a visible composition root.
- Prefer deterministic computation and policy enforcement; AI systems may interpret, explain, or route but do not silently bypass contracts.
- Keep development agents and operational agents distinct; external actions require authorization, approval, idempotency, and audit.
- Use synthetic or demonstrably public data only. This is an architectural lab, not a production procurement authority.
- Follow the repository constitution and ADRs for architecture changes; use benchmark evidence for model or algorithm swaps.

## Open decisions and questions

- Which append-only persistence/database adapter should follow the M7 port, and what temporal correction evidence is required? Start with [Issue #91](https://github.com/stauntonjr/procurement-intelligence-lab/issues/91) and ADR-015.
- Which retrieval projections and fusion strategy earn adoption under the M8 evaluation plan? Start with [Issues #54, #55, #57, and #59](https://github.com/stauntonjr/procurement-intelligence-lab/issues/59).
- Which review, guarded-action, and product-feedback slices should be sequenced next? Use the [milestone map](../development/milestone-map.md) and linked issue acceptance criteria.

## Recommended next work

1. Review and merge the active M7/related governance PRs only after their checks and acceptance evidence are current.
2. Continue M7 from Issue #91 and ADR-015; preserve append-only and temporal semantics.
3. Record any changed milestone/status mapping in the milestone map and update this index when the change materially affects onboarding.
4. Before selecting retrieval or agent frameworks, run the repository's stated evaluation and benchmark work.

## Refresh protocol

Treat this page as a concise index, not a second source of truth. On each meaningful change:

1. Read the relevant code, tests, ADRs, architecture docs, and GitHub Issue/PR.
2. Update this page only when the milestone, active work, settled decisions, or recommended next work changes materially.
3. Link to authoritative artifacts instead of copying their full content.
4. Do not persist hidden chain-of-thought or entire chat transcripts. Chat/Work is for exploration and planning; Codex and other development agents implement against the repository; GitHub docs, issues, ADRs, and PRs are the durable shared state.
5. Recheck links and run the lightweight documentation check before opening or updating a PR.
