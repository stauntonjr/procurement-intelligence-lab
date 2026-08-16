# Project handoff

## Purpose and use

This page is a concise orientation index for a fresh human or development agent. It explains where the current state is recorded and what to read first; it is not a transcript, decision log, or duplicate architecture specification.

Start with [AGENTS.md](../../AGENTS.md), then read the relevant [GitHub Issue](https://github.com/stauntonjr/procurement-intelligence-lab/issues), linked ADRs, and the authoritative documents below before changing the repository.

## Current milestone and status

- **M0 — Engineering and architecture harness:** active hardening. PR #119 delivered ADR-021, layered tests, package/UI smoke checks, C001-C008 deterministic oracles, and credentialed GitHub planning administration. Issues #110-#115 are complete; #145 is the bounded active semantic-loop slice and ends after one PR without expanding into prompt optimization. Issue #116 remains open until both protected baseline variants run, #120 remains open pending representative `uv` and bot-review evidence, and #121 is the current Actions supply-chain slice. Domain-package contracts #134-#135 are complete. See [Issue #109](https://github.com/stauntonjr/procurement-intelligence-lab/issues/109) under [Issue #3](https://github.com/stauntonjr/procurement-intelligence-lab/issues/3).
- **M4 — Reconciliation and governed state:** in progress. Explicit source precedence and state invariants are implemented, while the broader governing-claim contract in [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15) remains open.
- **M5 — Evidence-first UX:** in progress. The local inspector is runnable and now has a real HTTP happy-path check; [Issue #8](https://github.com/stauntonjr/procurement-intelligence-lab/issues/8) still governs the full drill-down showcase.
- **M6 — Retrieval:** in progress. The lexical lifecycle foundation exists and now rejects unsupported projection kinds; later adapters and evaluation remain.
- GitHub's M0-M9 milestones are canonical. `S0`-`S9` in the [milestone map](../development/milestone-map.md) describe historical implementation order only.

## Current architecture

The system preserves evidence from synthetic/semi-structured procurement documents through structured mapping, source assertions, entity mentions, resolution decisions, canonicalized assertions, reconciliation, operational state, and derived intelligence. Core semantics remain framework-independent; adapters own external mechanics. Postgres is the intended canonical store, while lexical, vector, and graph systems are replaceable projections. Deterministic services compute and enforce policy; AI-assisted interfaces explain and route work. The accepted horizontal platform contract separates stage definitions, domain bindings/policy, and runtime implementation selection; it is documented in [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md) and the [conformance contract](../architecture/domain-package-conformance.md), but is not implemented on `main`. Vertical-owned procurement semantics now live under `src/procurement_intelligence_lab/domains/procurement/`; horizontal package/compiler contracts remain under `src/procurement_intelligence_lab/domain/`. See [architecture overview](../architecture/overview.md), [semantic model](../domains/procurement/semantic-model.md), and [architecture tradeoffs](../architecture.md).

## Recently completed

- M0–M4 repository, evidence, claims, and constrained chat foundations.
- M5 local HTTP chat/evidence inspector; see [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82).
- M6 durable identifiers, source viewer, and review context; see [PR #86](https://github.com/stauntonjr/procurement-intelligence-lab/pull/86), [PR #88](https://github.com/stauntonjr/procurement-intelligence-lab/pull/88), and [PR #90](https://github.com/stauntonjr/procurement-intelligence-lab/pull/90).
- M7 ledger boundary and initial anomaly/execution-provenance contract; see [PR #92](https://github.com/stauntonjr/procurement-intelligence-lab/pull/92) and [PR #94](https://github.com/stauntonjr/procurement-intelligence-lab/pull/94).
- Deterministic PR checks with optional advisory AI review; see [PR #93](https://github.com/stauntonjr/procurement-intelligence-lab/pull/93). PR-triggered Gemini review and current-commit review-arrival polling were retired because quota exhaustion and bot self-updates made them nondeterministic merge blockers.
- Canonical shared project-memory convention; see [PR #96](https://github.com/stauntonjr/procurement-intelligence-lab/pull/96).
- M8 rebuildable lexical retrieval-projection lifecycle foundation; see [PR #101](https://github.com/stauntonjr/procurement-intelligence-lab/pull/101) and [ADR-018](../adr/018-rebuildable-retrieval-projections.md).
- M7.2 deterministic XLSX transformation provenance through source assertions; see [PR #102](https://github.com/stauntonjr/procurement-intelligence-lab/pull/102) and [ADR-017](../adr/017-execution-and-decision-provenance.md).
- M7 expected-versus-observed state projection, including scoped latest-as-of comparison; see [PR #105](https://github.com/stauntonjr/procurement-intelligence-lab/pull/105) and [ADR-020](../adr/020-expected-observed-state.md).
- Focused domain-logic review procedure for Copilot and Gemini; see [PR #106](https://github.com/stauntonjr/procurement-intelligence-lab/pull/106).
- Semantic-quality hardening: layered test taxonomy, clean-wheel and real HTTP smoke tests, explicit reconciliation policy, state invariants, and C001-C008 deterministic challenge oracles; see [PR #119](https://github.com/stauntonjr/procurement-intelligence-lab/pull/119) and [ADR-021](../adr/021-semantic-quality-and-agent-challenge-harness.md).
- M0.16 coverage ratchet: checked-in line/branch baseline, CI enforcement, and machine-readable public challenge run artifacts; see [Issue #112](https://github.com/stauntonjr/procurement-intelligence-lab/issues/112) and [PR #138](https://github.com/stauntonjr/procurement-intelligence-lab/pull/138).
- M0.19 public challenge evidence: known-bad manifest metadata, current-code oracle artifacts, executable mutation rejection, and CI publication; see [Issue #115](https://github.com/stauntonjr/procurement-intelligence-lab/issues/115), [PR #139](https://github.com/stauntonjr/procurement-intelligence-lab/pull/139), and [PR #144](https://github.com/stauntonjr/procurement-intelligence-lab/pull/144).
- M0.33 ratified the DomainPackage stage catalog, typed neutral modes, versioning policy, procurement mapping, and M0.34 conformance matrix; see [Issue #134](https://github.com/stauntonjr/procurement-intelligence-lab/issues/134) and [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md). The compiler, runtime planner, and package extraction remain future slices.
- Credentialed GitHub planning administration is reproducible through `.github/planning.json`, `tools/github_planning.py`, and `.agents/skills/manage-github-planning/SKILL.md`; Project #6 has the eight named operating views. The post-merge audit found 10 milestones, 28 labels, 25 Project fields, 98 Project items, and no missing configured planning objects.

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
- Which retrieval projections and fusion strategy earn adoption under the M8 evaluation plan? Start with [Issue #55](https://github.com/stauntonjr/procurement-intelligence-lab/issues/55), [Issue #57](https://github.com/stauntonjr/procurement-intelligence-lab/issues/57), and [Issue #59](https://github.com/stauntonjr/procurement-intelligence-lab/issues/59).
- Which review, guarded-action, and product-feedback slices should be sequenced next? Use the [milestone map](../development/milestone-map.md) and linked issue acceptance criteria.
- Which manifest encoding, typed diagnostics, and conformance fixtures should implement the accepted DomainPackage contract without altering procurement semantics? See [Issue #135](https://github.com/stauntonjr/procurement-intelligence-lab/issues/135), [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md), and the [conformance contract](../architecture/domain-package-conformance.md).

## Recommended next work

1. Complete [Issue #145](https://github.com/stauntonjr/procurement-intelligence-lab/issues/145)'s bounded semantic specification, implementation, verification, and review loop, then stop harness expansion and reassess priority.
2. Return to product work: complete [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15)'s governing-claim policy before continuing [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60)'s anomaly orchestration.
3. Complete and merge [Issue #121](https://github.com/stauntonjr/procurement-intelligence-lab/issues/121)'s immutable Actions policy independently; do not make it a prerequisite for resumed product work.
4. Run [Issue #116](https://github.com/stauntonjr/procurement-intelligence-lab/issues/116)'s protected baselines only after a model adapter and configuration are explicitly authorized; do not treat the credential-free smoke as a score.
5. Keep DSPy or other prompt/program optimization deferred until the baseline exists and a separate benchmark issue defines train/development/held-out separation and an exit criterion.

## Refresh protocol

Treat this page as a concise index, not a second source of truth. On each meaningful change:

1. Read the relevant code, tests, ADRs, architecture docs, and GitHub Issue/PR.
2. Update this page only when the milestone, active work, settled decisions, or recommended next work changes materially.
3. Link to authoritative artifacts instead of copying their full content.
4. Do not persist hidden chain-of-thought or entire chat transcripts. Chat/Work is for exploration and planning; Codex and other development agents implement against the repository; GitHub docs, issues, ADRs, and PRs are the durable shared state.
5. Use the roadmap stewardship audit to flag drift, but record material chat decisions deliberately in durable artifacts.
6. Recheck links and run the lightweight documentation check before opening or updating a PR.
