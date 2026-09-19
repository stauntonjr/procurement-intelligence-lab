# Project handoff

## Purpose and use

This page is a concise orientation index for a fresh human or development agent. It explains where the current state is recorded and what to read first; it is not a transcript, decision log, or duplicate architecture specification.

Start with [AGENTS.md](../../AGENTS.md), then read the relevant [GitHub Issue](https://github.com/stauntonjr/procurement-intelligence-lab/issues), linked ADRs, and the authoritative documents below before changing the repository.

## Current milestone and status

Status refreshed against GitHub Issues and merged PRs on 2026-09-18. This refresh does not certify live Project fields or deployment state.

- **M0 — Engineering and architecture harness:** active hardening. Issue #16's repository bootstrap and package-boundary acceptance is verified complete; [Issue #17](https://github.com/stauntonjr/procurement-intelligence-lab/issues/17)'s development conventions and typed error contract are complete through [PR #154](https://github.com/stauntonjr/procurement-intelligence-lab/pull/154). PR #119 delivered ADR-021, layered tests, package/UI smoke checks, and the initial C001-C008 deterministic oracles; C009 covers platform-to-vertical dependency inversion, C010 covers the universal stage-contract registry, and C011 covers bounded generated Dependabot pull requests. Issues #110-#115 and #145 are complete; #116 remains open until both protected baseline variants run, #120 remains open pending representative update evidence, and #121 remains open for full Actions supply-chain acceptance. Domain-package contracts #134-#135 are complete. [Issue #149](https://github.com/stauntonjr/procurement-intelligence-lab/issues/149) completed platform-versus-procurement ownership separation and BoQ/PO pressure tests in [PR #150](https://github.com/stauntonjr/procurement-intelligence-lab/pull/150); [Issue #151](https://github.com/stauntonjr/procurement-intelligence-lab/issues/151) completed concrete semantic contracts across all twelve logical stages in [PR #152](https://github.com/stauntonjr/procurement-intelligence-lab/pull/152). See [Issue #5](https://github.com/stauntonjr/procurement-intelligence-lab/issues/5) and [Issue #109](https://github.com/stauntonjr/procurement-intelligence-lab/issues/109) under [Issue #3](https://github.com/stauntonjr/procurement-intelligence-lab/issues/3).
- **M4 — Reconciliation and governed state:** governed required-quantity decisions now project into typed expected state while retaining unresolved claims and evidence. Issue #15 is pending its final acceptance audit and close-out.
- **M5 — Evidence-first UX:** in progress. The local inspector is runnable and now has a real HTTP happy-path check; [Issue #8](https://github.com/stauntonjr/procurement-intelligence-lab/issues/8) still governs the full drill-down showcase.
- **M6 — Retrieval:** in progress. The lexical lifecycle foundation exists and now rejects unsupported projection kinds; later adapters and evaluation remain.
- GitHub's M0-M9 milestones are canonical. `S0`-`S9` in the [milestone map](../development/milestone-map.md) describe historical implementation order only.

## Current architecture

The system preserves evidence from synthetic/semi-structured procurement documents through structured mapping, source assertions, entity mentions, resolution decisions, canonicalized assertions, reconciliation, operational state, and derived intelligence. Core semantics remain framework-independent; adapters own external mechanics. Postgres is the intended canonical store, while lexical, vector, and graph systems are replaceable projections. Deterministic services compute and enforce policy; AI-assisted interfaces explain and route work. Shared semantic contracts and the DomainPackage compiler live under `src/procurement_intelligence_lab/platform/`; vertical-owned BOM, BoQ, PO, procurement state, reconciliation, and anomaly behavior lives under `src/procurement_intelligence_lab/domains/procurement/`. Platform and ports never import a concrete vertical. The complete semantic topology does not imply complete procurement execution; see [universal stage semantics](../architecture/universal-stage-semantics.md), [platform semantics and vertical ownership](../architecture/platform-semantics.md), [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md), the [conformance contract](../architecture/domain-package-conformance.md), [semantic model](../domains/procurement/semantic-model.md), and [architecture tradeoffs](../architecture.md).

## Recently completed

- The local inspector now presents readable claim values, clickable evidence and execution stages,
  and original XLSX source-row values with EvidenceRef-highlighted cells. The README includes an actual-browser
  animation. See [demo acceptance](inspector-demo-acceptance.md); this is a bounded Issue #50 slice,
  not completion of the full inspector or original-document viewer milestones.
- M0–M4 repository, evidence, claims, and constrained chat foundations.
- M5 local HTTP chat/evidence inspector; see [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82).
- Durable identifiers, source viewer, and review context; see [PR #86](https://github.com/stauntonjr/procurement-intelligence-lab/pull/86), [PR #88](https://github.com/stauntonjr/procurement-intelligence-lab/pull/88), and [PR #90](https://github.com/stauntonjr/procurement-intelligence-lab/pull/90).
- M7 ledger boundary and initial anomaly/execution-provenance contract; see [PR #92](https://github.com/stauntonjr/procurement-intelligence-lab/pull/92) and [PR #94](https://github.com/stauntonjr/procurement-intelligence-lab/pull/94).
- Deterministic PR checks with optional advisory AI review; see [PR #93](https://github.com/stauntonjr/procurement-intelligence-lab/pull/93). PR-triggered Gemini review and current-commit review-arrival polling were retired because quota exhaustion and bot self-updates made them nondeterministic merge blockers.
- Canonical shared project-memory convention; see [PR #96](https://github.com/stauntonjr/procurement-intelligence-lab/pull/96).
- M6 rebuildable lexical retrieval-projection lifecycle foundation; see [PR #101](https://github.com/stauntonjr/procurement-intelligence-lab/pull/101) and [ADR-018](../adr/018-rebuildable-retrieval-projections.md).
- M7.2 deterministic XLSX transformation provenance through source assertions; see [PR #102](https://github.com/stauntonjr/procurement-intelligence-lab/pull/102) and [ADR-017](../adr/017-execution-and-decision-provenance.md).
- M4 expected-versus-observed state projection, including scoped latest-as-of comparison; see [PR #105](https://github.com/stauntonjr/procurement-intelligence-lab/pull/105) and [ADR-020](../adr/020-expected-observed-state.md).
- Focused domain-logic review procedure for Copilot and Gemini; see [PR #106](https://github.com/stauntonjr/procurement-intelligence-lab/pull/106).
- Semantic-quality hardening: layered test taxonomy, clean-wheel and real HTTP smoke tests, explicit reconciliation policy, state invariants, and C001-C008 deterministic challenge oracles; see [PR #119](https://github.com/stauntonjr/procurement-intelligence-lab/pull/119) and [ADR-021](../adr/021-semantic-quality-and-agent-challenge-harness.md).
- M0.16 coverage ratchet: checked-in line/branch baseline, CI enforcement, and machine-readable public challenge run artifacts; see [Issue #112](https://github.com/stauntonjr/procurement-intelligence-lab/issues/112) and [PR #138](https://github.com/stauntonjr/procurement-intelligence-lab/pull/138).
- M0.19 public challenge evidence: known-bad manifest metadata, current-code oracle artifacts, executable mutation rejection, and CI publication; see [Issue #115](https://github.com/stauntonjr/procurement-intelligence-lab/issues/115), [PR #139](https://github.com/stauntonjr/procurement-intelligence-lab/pull/139), and [PR #144](https://github.com/stauntonjr/procurement-intelligence-lab/pull/144).
- M0.33 ratified the DomainPackage stage catalog, typed neutral modes, versioning policy, procurement mapping, and M0.34 conformance matrix; see [Issue #134](https://github.com/stauntonjr/procurement-intelligence-lab/issues/134) and [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md). Runtime planning and complete procurement package extraction remain future slices.
- M0.34 delivered the deterministic DomainPackage compiler. [Issue #149](https://github.com/stauntonjr/procurement-intelligence-lab/issues/149) completed the ownership correction and initial BoQ/PO pressure tests through PR #150; [Issue #151](https://github.com/stauntonjr/procurement-intelligence-lab/issues/151) completed typed logical-stage semantics and registry enforcement through PR #152. Both issues are closed; runtime planning and complete procurement execution remain separate work.
- M0.2 development conventions and stable typed error contracts are complete through [PR #154](https://github.com/stauntonjr/procurement-intelligence-lab/pull/154).
- Credentialed GitHub planning administration is reproducible through `.github/planning.json`, `tools/github_planning.py`, and `.agents/skills/manage-github-planning/SKILL.md`; the prior post-merge audit recorded eight named operating views in Project #6 and found 10 milestones, 28 labels, 25 Project fields, 98 Project items, and no missing configured planning objects. Those counts are historical, not a fresh Project audit.

## Active work and PRs

- [Issue #47](https://github.com/stauntonjr/procurement-intelligence-lab/issues/47) is complete. [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60) remains open: proceed with deterministic orchestration only after the governing-claim policy in Issue #15 is complete, using explicit scoped expected and observed state.
- [Issue #54](https://github.com/stauntonjr/procurement-intelligence-lab/issues/54) remains open despite the delivered lexical lifecycle foundation and unsupported-kind rejection; reconcile its full acceptance evidence before closure. Follow-on M6 work includes [Issues #55, #57, #59, #62, and #63](https://github.com/stauntonjr/procurement-intelligence-lab/issues/63); preserve their dependencies and evaluation gates.
- Identity, source-viewer, and review-context slices are complete; see [Issues #85, #87, and #89](https://github.com/stauntonjr/procurement-intelligence-lab/issues/89).

## Settled decisions

- Preserve provenance and source assertions; do not turn extraction or similarity into truth.
- Keep domain semantics framework- and database-independent, with explicit ports, adapters, dependency injection, and a visible composition root.
- Prefer deterministic computation and policy enforcement; AI systems may interpret, explain, or route but do not silently bypass contracts.
- Keep development agents and operational agents distinct; external actions require authorization, approval, idempotency, and audit.
- Use synthetic or demonstrably public data only. This is an architectural lab, not a production procurement authority.
- Follow the repository constitution and ADRs for architecture changes; use benchmark evidence for model or algorithm swaps.
- Execution/decision provenance is an immutable event graph concept; relational foreign keys are a persistence mechanism, not the conceptual model. See [Issue #98](https://github.com/stauntonjr/procurement-intelligence-lab/issues/98).

## Open decisions and questions

- The governing-claim authority and temporal policy is ratified in [ADR-023](../adr/023-predicate-specific-governing-claim-policy.md), with governed state projection identity in [ADR-024](../adr/024-governed-state-projection-identity.md). Reconcile the merged implementation against [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15) before closing it.
- How should the request-scope contract evolve from the synthetic fixture boundary to authenticated multi-project adapters? See [ADR-019](../adr/019-explicit-request-scope.md).
- Which retrieval projections and fusion strategy earn adoption under the M6 evaluation plan? Start with [Issue #55](https://github.com/stauntonjr/procurement-intelligence-lab/issues/55), [Issue #57](https://github.com/stauntonjr/procurement-intelligence-lab/issues/57), and [Issue #59](https://github.com/stauntonjr/procurement-intelligence-lab/issues/59).
- Which review, guarded-action, and product-feedback slices should be sequenced next? Use the [milestone map](../development/milestone-map.md) and linked issue acceptance criteria.
- Which runtime registry, capability-validation, and logical-to-physical planning slice should follow the completed DomainPackage compiler without introducing domain-name branching? Create a scoped issue before scheduling it; use [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md) and the [architecture contract](../architecture/domain-package-and-stage-planning.md) as its constraints.

## Recommended next work

The owner prioritizes independent employer-facing showcases for Procurement Intelligence Lab and
SciFact RAG, with explicit integration planning. See the [parallel product development plan](parallel-product-development.md).
Package the current runnable procurement slice for demonstration while keeping broader product
acceptance below separate; SciFact research and shared-platform migration are not showcase prerequisites.

The next showcase improvements are sequenced in the [showcase maturity plan](../superpowers/plans/2026-09-18-procurement-showcase-maturity.md): freeze a discrepancy contract, implement its governing decision, explain it in the UI, highlight original XLSX cells, and record a clearer walkthrough. This is planned work, not delivered capability.

Public hosting is a separate, planned showcase slice. The verified VPS deployment convention and
acceptance boundary for `procurement.ediacarian.dedyn.io` are in the
[VPS deployment plan](../superpowers/plans/2026-09-18-vps-procurement-inspector.md).

1. Return to product work: use the governed expected/observed state path from [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15) when continuing [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60)'s anomaly orchestration.
2. Reconcile the delivered work against the still-open acceptance of [Issue #54](https://github.com/stauntonjr/procurement-intelligence-lab/issues/54) and [Issue #121](https://github.com/stauntonjr/procurement-intelligence-lab/issues/121); do not infer closure from implementation alone.
3. Run [Issue #116](https://github.com/stauntonjr/procurement-intelligence-lab/issues/116)'s protected baselines only after a model adapter and configuration are explicitly authorized; do not treat the credential-free smoke as a score.
4. Keep DSPy or other prompt/program optimization deferred until the baseline exists and a separate benchmark issue defines train/development/held-out separation and an exit criterion.

## Refresh protocol

Treat this page as a concise index, not a second source of truth. On each meaningful change:

1. Read the relevant code, tests, ADRs, architecture docs, and GitHub Issue/PR.
2. Update this page only when the milestone, active work, settled decisions, or recommended next work changes materially.
3. Link to authoritative artifacts instead of copying their full content.
4. Do not persist hidden chain-of-thought or entire chat transcripts. Chat/Work is for exploration and planning; Codex and other development agents implement against the repository; GitHub docs, issues, ADRs, and PRs are the durable shared state.
5. Use the roadmap stewardship audit to flag drift, but record material chat decisions deliberately in durable artifacts.
6. Recheck links and run the lightweight documentation check before opening or updating a PR.
