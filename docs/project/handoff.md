# Project handoff

## Purpose and use

This page is a concise orientation index for a fresh human or development agent. It explains where the current state is recorded and what to read first; it is not a transcript, decision log, or duplicate architecture specification.

Start with [AGENTS.md](../../AGENTS.md), then read the relevant [GitHub Issue](https://github.com/stauntonjr/procurement-intelligence-lab/issues), linked ADRs, and the authoritative documents below before changing the repository.

## Current milestone and status

- **M7 — Append-only persistence, temporal/as-of state, anomaly taxonomy, and execution provenance:** in progress. The ledger boundary and the first anomaly/provenance contract are on `main`; remaining work includes temporal correction, durable storage, and anomaly orchestration. See the [canonical milestone map](../development/milestone-map.md) and [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60).
- **M8 — Retrieval projections and review UI:** in progress. The rebuildable projection lifecycle foundation is complete; later adapter work remains. See [Issue #54](https://github.com/stauntonjr/procurement-intelligence-lab/issues/54).
- **M9 — Guarded actions, product signals, and integrated evaluation:** planned.
- The initial M0–M6 evidence-first vertical slice is complete on `main`; the [root README](../../README.md) records the current product boundary and runnable entry points.

## Current architecture

The system preserves evidence from synthetic/semi-structured procurement documents through structured mapping, source assertions, entity mentions, resolution decisions, canonicalized assertions, reconciliation, operational state, and derived intelligence. Core semantics remain framework-independent; adapters own external mechanics. Postgres is the intended canonical store, while lexical, vector, and graph systems are replaceable projections. Deterministic services compute and enforce policy; AI-assisted interfaces explain and route work. See [architecture overview](../architecture/overview.md), [semantic model](../domain/semantic-model.md), and [architecture tradeoffs](../architecture.md).

## Recently completed

- M0–M4 repository, evidence, claims, and constrained chat foundations.
- M5 local HTTP chat/evidence inspector; see [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82).
- M6 durable identifiers, source viewer, and review context; see [PR #86](https://github.com/stauntonjr/procurement-intelligence-lab/pull/86), [PR #88](https://github.com/stauntonjr/procurement-intelligence-lab/pull/88), and [PR #90](https://github.com/stauntonjr/procurement-intelligence-lab/pull/90).
- M7 ledger boundary and initial anomaly/execution-provenance contract; see [PR #92](https://github.com/stauntonjr/procurement-intelligence-lab/pull/92) and [PR #94](https://github.com/stauntonjr/procurement-intelligence-lab/pull/94).
- Layered deterministic and advisory PR review governance; see [PR #93](https://github.com/stauntonjr/procurement-intelligence-lab/pull/93).
- Canonical shared project-memory convention; see [PR #96](https://github.com/stauntonjr/procurement-intelligence-lab/pull/96).
- M8 rebuildable lexical retrieval-projection lifecycle foundation; see [PR #101](https://github.com/stauntonjr/procurement-intelligence-lab/pull/101) and [ADR-018](../adr/018-rebuildable-retrieval-projections.md).
- M7.2 deterministic XLSX transformation provenance through source assertions; see [PR #102](https://github.com/stauntonjr/procurement-intelligence-lab/pull/102) and [ADR-017](../adr/017-execution-and-decision-provenance.md).
- M7 expected-versus-observed state projection, including scoped latest-as-of comparison; see [PR #105](https://github.com/stauntonjr/procurement-intelligence-lab/pull/105) and [ADR-020](../adr/020-expected-observed-state.md).
- Focused domain-logic review procedure for Copilot and Gemini; see [PR #106](https://github.com/stauntonjr/procurement-intelligence-lab/pull/106).

## Active work and PRs

- [Issue #47](https://github.com/stauntonjr/procurement-intelligence-lab/issues/47) is complete. [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60) is active: begin deterministic orchestration only from explicit scoped expected and observed state.
- [Issue #54](https://github.com/stauntonjr/procurement-intelligence-lab/issues/54) is complete. Follow-on M8 work includes [Issues #55, #57, #59, #62, and #63](https://github.com/stauntonjr/procurement-intelligence-lab/issues/63); preserve their dependencies and evaluation gates.
- M6 identity, source-viewer, and review-context work is complete; see [Issues #85, #87, and #89](https://github.com/stauntonjr/procurement-intelligence-lab/issues/89).

## Settled decisions

- Preserve provenance and source assertions; do not turn extraction or similarity into truth.
- Keep domain semantics framework- and database-independent, with explicit ports, adapters, dependency injection, and a visible composition root.
- Prefer deterministic computation and policy enforcement; AI systems may interpret, explain, or route but do not silently bypass contracts.
- Keep development agents and operational agents distinct; external actions require authorization, approval, idempotency, and audit.
- Use synthetic or demonstrably public data only. This is an architectural lab, not a production procurement authority.
- Follow the repository constitution and ADRs for architecture changes; use benchmark evidence for model or algorithm swaps.
- Execution/decision provenance is an immutable event graph concept; relational foreign keys are a persistence mechanism, not the conceptual model. See [Issue #98](https://github.com/stauntonjr/procurement-intelligence-lab/issues/98).

## Open decisions and questions

- How should scoped expected and observed procurement records be populated from append-only inputs, and what temporal correction evidence is required? Start with [Issue #47](https://github.com/stauntonjr/procurement-intelligence-lab/issues/47) and [Issue #91](https://github.com/stauntonjr/procurement-intelligence-lab/issues/91).
- How should the request-scope contract evolve from the synthetic fixture boundary to authenticated multi-project adapters? See [ADR-019](../adr/019-explicit-request-scope.md).
- Which retrieval projections and fusion strategy earn adoption under the M8 evaluation plan? Start with [Issues #55, #57, and #59](https://github.com/stauntonjr/procurement-intelligence-lab/issues/59).
- Which review, guarded-action, and product-feedback slices should be sequenced next? Use the [milestone map](../development/milestone-map.md) and linked issue acceptance criteria.

## Recommended next work

1. Extend [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60) from explicit scoped expected and observed state; keep anomaly detection distinct from prediction, decisions, and actions.
2. Run the [roadmap stewardship protocol](../development/roadmap-stewardship.md) and resolve confirmed durable-record drift through normal Issues and PRs.
3. Sequence later retrieval adapters only after their prerequisites, scope filters, and evaluation evidence are ready.
4. Before selecting retrieval or agent frameworks, run the repository's stated evaluation and benchmark work.

## Refresh protocol

Treat this page as a concise index, not a second source of truth. On each meaningful change:

1. Read the relevant code, tests, ADRs, architecture docs, and GitHub Issue/PR.
2. Update this page only when the milestone, active work, settled decisions, or recommended next work changes materially.
3. Link to authoritative artifacts instead of copying their full content.
4. Do not persist hidden chain-of-thought or entire chat transcripts. Chat/Work is for exploration and planning; Codex and other development agents implement against the repository; GitHub docs, issues, ADRs, and PRs are the durable shared state.
5. Use the roadmap stewardship audit to flag drift, but record material chat decisions deliberately in durable artifacts.
6. Recheck links and run the lightweight documentation check before opening or updating a PR.
