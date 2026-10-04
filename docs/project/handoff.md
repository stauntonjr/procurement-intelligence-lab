# Project handoff

## G2 installed evidence consolidation — 2026-10-04

`codex/g2-evidence-consolidation` stacks on draft #189, unmerged. Hash-bound compiler reconciles
fresh language48/48, original three-scenario9/9, adversarial9/9 and a new installed deterministic
48/48/464source timing run, with zero new inference. Prior controls25/28 and candidate26/28 remain
visible as inspected development; populations are not pooled. [Dossier, latency scopes and ordered
remaining work](g2-acceptance-dossier.md). Bounded installed suite passes; full G2/release, actual
browser error/accessibility coverage, measured presentation, main integration and deployment remain
open. B2 stays gated; source corpus unchanged. Unknown evidence/cost is notzero. Next bounded work:
#74 actual browser async/error recovery, then reviewer rehearsal and separately authorized rollout.

## Installed G2 adversarial acceptance — 2026-10-04

`codex/g2-adversarial-acceptance` is stacked on draft #188, unmerged. Nine installed HTTP/process
guards pass: five real Qwen attempts plus three controlled protocol attempts; seven tool starts,
one expected failed tool, three original approval receipts and one exact save preserved through
actual post-save exit86/restart/repeated approval. Complete causal/run/receipt evidence is required;
one independent evaluator Important finding fixed by six RED/GREEN regressions, 695 full tests.
[Contract, compact outcomes and remaining gates](g2-adversarial-acceptance.md). This is bounded
failure acceptance; full G2/release consolidation, comprehensive accessibility, deployment and B2
expansion remain separate open gates. Source corpus remains four projects/24workbooks/960rows;
historical language/control misses remain immutable. No runtime/model/prompt/source/package change.

## Fresh language v3 candidate evaluation — 2026-10-04

`codex/fresh-language-v3-evaluation` is stacked on draft #187, unmerged. Frozen cutoff candidate
and new question wording pass 48/48: root 24, independent validation 12/test 12. Installed gold 48/48
and 464 source checks; 48 actual terminal calls, 56 tool starts, 28 exact saves. See
[provenance/results/remaining gates](fresh-language-v3-evaluation.md). Version3 includes retired
language/control lineage; historical version2 remains unchanged. Independent evaluator review and
explicit author data/results audit passed. This is language-only evidence over known correlated
sources, not source expansion or broad accuracy. Full G2 adversarial/release, comprehensive browser
accessibility, deployment and B2 expansion remain separate open gates. Historical control misses
remain retained.

## Cutoff intent development continuation — 2026-10-04

`codex/cutoff-intent-development` is stacked on draft #186. Matching review-cutoff wording is
request metadata, with existing scope/date/item and human-save guards. Baseline 25/28 includes
a conflicting-date routing failure; candidate 26/28 retains two safe supported-request abstentions.
Candidate inspected-language regression 48/48 and original browser 9/9 pass: 113 actual calls,
124 tool starts and 36 saves. See [results/limits](cutoff-intent-development.md).
The prior fresh-language cohort is retired as inspected development data before tuning. Full G2
remains not_ready; new independent evaluation, release/deployment and expansion gates remain open.

## Fresh language evaluation continuation — 2026-10-04

`codex/fresh-language-evaluation` is stacked on draft PR #185. Unchanged runtime/source
scenarios with new independently authored validation/test wording: 23/24 pass, one safe unsupported
miss on a valid explicit-cutoff Cinder query. Root development 24/24; total 47/48. Installed gold
48/48 plus 464 source checks, 48 actual calls, 54 tool starts, 27 exact saves. See
[provenance/results/limits](fresh-language-evaluation.md). This new language cohort is now
retired as inspected development data; see the cutoff continuation above. Unmerged, not_ready
for bounded live acceptance/full G2;
no new source-data independence or corpus expansion.

## Original showcase live continuation — 2026-10-04

`codex/original-showcase-live` is stacked on draft PR #184. Three original January source
snapshots now use the existing live review workflow with original policy/evidence identities.
Nine authored browser trials pass: nine model calls, eighteen tool starts, eighteen source checks,
three process recoveries and eight exact saves. Unresolved requirements retain observed order 2
while remaining `not_assessed`. See [contract/results/limits](original-showcase-live.md).
Unmerged; fresh held-out evaluation, full G2 and deployment remain open. No corpus expansion.

## Active real-browser acceptance continuation — 2026-10-04

`codex/browser-live-acceptance`, stacked on draft PR #183, verifies a clean installed
reviewer in actual local headless Chromium. Keyboard sign-in/focus contrast and narrow
identifier wrapping are fixed. Three fixture and 14 authored live Qwen browser submissions
pass source/review/restart/save accounting; eight live saves, four tool-free abstentions,
and two rejected investigations. See [walkthrough, artifacts and remaining gates](browser-live-acceptance.md)
and [compact versions/results](browser-live-results.json). This is branch work, not main,
held-out quality, comprehensive accessibility or deployment. Fresh evaluation and full G2/release acceptance remain open; original tiny-fixture
live routing is documented above; corpus expansion stays gated.

## Active local browser review continuation — 2026-10-03

`codex/browser-review-workflow` is stacked on open PR #179. It adds a loopback-only
synthetic human reviewer, owned run discovery, exact approve/reject and recovery controls,
scoped source cells and an application audit snapshot timeline. See
[ADR-031](../adr/031-local-browser-review-transport.md),
[public command and contract](../product/local-browser-review-v1.md) and
[verification boundary](local-browser-review-evidence.md). Actual browser interaction,
accessibility, deployment, streaming and live-model acceptance remain open; this slice is
a draft continuation of #74, not a complete demo release.

## Fixture checkpoint foundation — 2026-10-03

`codex/serial-review-workflow` builds on open PR #178, adding the optional serial LangGraph
prototype behind a repository-owned runtime port. See [ADR-030](../adr/030-optional-serial-review-workflow.md),
[contract and CLI](../product/serial-review-workflow-v1.md) and
[execution evidence](serial-review-workflow-evidence.md). Typed fixture inputs, persisted
exact review and crash recovery precede natural-language/model and browser work. This is
branch work; it does not update `main`, deployment or live acceptance.

## Purpose and use

This page is a concise orientation index for a fresh human or development agent. It explains where the current state is recorded and what to read first; it is not a transcript, decision log, or duplicate architecture specification.

Start with [AGENTS.md](../../AGENTS.md), then read the relevant [GitHub Issue](https://github.com/stauntonjr/procurement-intelligence-lab/issues), linked ADRs, and the authoritative documents below before changing the repository.

## Current milestone and status

Status refreshed against GitHub Issues and merged PRs on 2026-09-19. This refresh does not certify live Project fields or deployment state.

- **M0 — Engineering and architecture harness:** active hardening. Issue #16's repository bootstrap and package-boundary acceptance is verified complete; [Issue #17](https://github.com/stauntonjr/procurement-intelligence-lab/issues/17)'s development conventions and typed error contract are complete through [PR #154](https://github.com/stauntonjr/procurement-intelligence-lab/pull/154). PR #119 delivered ADR-021, layered tests, package/UI smoke checks, and the initial C001-C008 deterministic oracles; C009 covers platform-to-vertical dependency inversion, C010 covers the universal stage-contract registry, and C011 covers bounded generated Dependabot pull requests. Issues #110-#115 and #145 are complete; #116 remains open until both protected baseline variants run, #120 remains open pending representative update evidence, and #121 remains open for full Actions supply-chain acceptance. Domain-package contracts #134-#135 are complete. [Issue #149](https://github.com/stauntonjr/procurement-intelligence-lab/issues/149) completed platform-versus-procurement ownership separation and BoQ/PO pressure tests in [PR #150](https://github.com/stauntonjr/procurement-intelligence-lab/pull/150); [Issue #151](https://github.com/stauntonjr/procurement-intelligence-lab/issues/151) completed concrete semantic contracts across all twelve logical stages in [PR #152](https://github.com/stauntonjr/procurement-intelligence-lab/pull/152). See [Issue #5](https://github.com/stauntonjr/procurement-intelligence-lab/issues/5) and [Issue #109](https://github.com/stauntonjr/procurement-intelligence-lab/issues/109) under [Issue #3](https://github.com/stauntonjr/procurement-intelligence-lab/issues/3).
- **M4 — Reconciliation and governed state:** governed required-quantity decisions now project into typed expected state while retaining unresolved claims and evidence. Issue #15 is closed through PR #161; remaining M4 acceptance stays issue-driven.
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

- Intent development on `codex/intent-contract-development`, stacked on PR182: requirement governance and document approval applicability clarified with unchanged deterministic/human authority. Final installed development regression46/48 (prior frozen pilot41/48); separate controls18/20, with safe boundary abstentions retained. The rejected candidate's unsafe date interpretations remain recorded. All prior split cases are now inspected development data, never fresh held-out evidence. See [experiment, limits and next work](intent-contract-development.md). Fresh evaluation and full G2/browser/release gates precede expansion.

- Frozen G2 pilot evaluation on `codex/g2-pilot-evaluation`, stacked on draft PR #181: installed deterministic HTTP 48/48 and 464 original source checks passed; live intent/end-to-end target checks 41/48, with seven unexpected abstentions retained. Independent ledger: 48 inference attempts, 42 tool starts, 21 single saved results. See [evaluation and next work](g2-pilot-evaluation.md). Prioritize development-only interpretation improvements and fresh frozen evaluation; full G2/browser/deployment and expansion gates remain open.

- Local Qwen live interpretation is implemented on `codex/local-qwen-interpretation`, stacked on the PR #180 browser draft: same owned run, strict scope/date/item proposal, durable redacted inference journal, existing deterministic brief and human review. Nine repeated development CLI walkthroughs and four live abstentions passed; installed authenticated live HTTP restart/save also passed. See [ADR-032](../adr/032-local-model-intent-and-journal.md), [caller contract](../product/local-qwen-review-v1.md), and [evidence and limits](local-qwen-review-evidence.md). Broader #53/#72 and full G2, actual browser/deployed acceptance remain open; no dataset expansion yet.

- [Issue #47](https://github.com/stauntonjr/procurement-intelligence-lab/issues/47) and [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60) are complete. [PR #174](https://github.com/stauntonjr/procurement-intelligence-lab/pull/174) merged the bounded assertion/line identity, lifecycle identity, and schedule-supersession corrections with C014-C016 evidence; `main` includes them at `b0cc77e`.
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

- The governing-claim authority and temporal policy is ratified in [ADR-023](../adr/023-predicate-specific-governing-claim-policy.md), with governed state projection identity in [ADR-024](../adr/024-governed-state-projection-identity.md). [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15) is closed after PR #161 integrated governed state projection.
- How should the request-scope contract evolve from the synthetic fixture boundary to authenticated multi-project adapters? See [ADR-019](../adr/019-explicit-request-scope.md).
- Which retrieval projections and fusion strategy earn adoption under the M6 evaluation plan? Start with [Issue #55](https://github.com/stauntonjr/procurement-intelligence-lab/issues/55), [Issue #57](https://github.com/stauntonjr/procurement-intelligence-lab/issues/57), and [Issue #59](https://github.com/stauntonjr/procurement-intelligence-lab/issues/59).
- Which review, guarded-action, and product-feedback slices should be sequenced next? Use the [milestone map](../development/milestone-map.md) and linked issue acceptance criteria.
- Which runtime registry, capability-validation, and logical-to-physical planning slice should follow the completed DomainPackage compiler without introducing domain-name branching? Create a scoped issue before scheduling it; use [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md) and the [architecture contract](../architecture/domain-package-and-stage-planning.md) as its constraints.

## Recommended next work

The [LangChain Academy reference notes](../langchain-ref/README.md) capture selected official
course-code patterns for the planned evidence-review agent, with pinned source revisions,
current-API caveats, an offline evaluator example, and Issue-specific acceptance checks.
They are reference material, not implemented agent capability or live evaluation evidence.

The owner prioritizes independent employer-facing showcases for Procurement Intelligence Lab and
SciFact RAG, with explicit integration planning. See the [parallel product development plan](parallel-product-development.md).
Use the current showcase packet for demonstration while keeping broader product acceptance
below separate; SciFact research and shared-platform migration are not showcase prerequisites.

The [reviewable showcase packet](showcase-walkthrough.md) records the merged discrepancy scenarios, source cells, captions, and reproducible offline/reset checks. PR #168 adds the bounded synthetic-order comparison on top of that packet. The [showcase maturity plan](../superpowers/plans/2026-09-18-procurement-showcase-maturity.md) remains the historical slice plan; these slices do not complete the broader M5/M7/M9 issues.

The synthetic Inspector is publicly available at
[procurement.ediacarian.dedyn.io](https://procurement.ediacarian.dedyn.io/). The verified VPS
deployment convention, release boundary, and evidence are in the
[VPS deployment plan](../superpowers/plans/2026-09-18-vps-procurement-inspector.md) and its
[deployment evidence note](procurement-vps-deployment-2026-09-19.md). It remains a synthetic,
read-only showcase rather than a production procurement system.

1. Reconcile the delivered work against the still-open acceptance of [Issue #54](https://github.com/stauntonjr/procurement-intelligence-lab/issues/54) and [Issue #121](https://github.com/stauntonjr/procurement-intelligence-lab/issues/121); do not infer closure from implementation alone.
2. Run [Issue #116](https://github.com/stauntonjr/procurement-intelligence-lab/issues/116)'s protected baselines only after a model adapter and configuration are explicitly authorized; do not treat the credential-free smoke as a score.
3. Keep DSPy or other prompt/program optimization deferred until the baseline exists and a separate benchmark issue defines train/development/held-out separation and an exit criterion.

## Refresh protocol

Treat this page as a concise index, not a second source of truth. On each meaningful change:

1. Read the relevant code, tests, ADRs, architecture docs, and GitHub Issue/PR.
2. Update this page only when the milestone, active work, settled decisions, or recommended next work changes materially.
3. Link to authoritative artifacts instead of copying their full content.
4. Do not persist hidden chain-of-thought or entire chat transcripts. Chat/Work is for exploration and planning; Codex and other development agents implement against the repository; GitHub docs, issues, ADRs, and PRs are the durable shared state.
5. Use the roadmap stewardship audit to flag drift, but record material chat decisions deliberately in durable artifacts.
6. Recheck links and run the lightweight documentation check before opening or updating a PR.

## Historical bounded Issue #60 order comparison

The inspector's synthetic order scenarios compare a governed requirement with a fixture-pinned
order quantity using the existing deterministic quantity-mismatch detector. A 4-versus-2 case
shows a mismatch with both sources; 4-versus-4 matches. Missing observations and unresolved
requirements remain not assessed, with null quantities and explicit reasons. See the
[acceptance contract](../product/showcase-order-comparison.md). This is not general PO ingestion,
a missing-PO conclusion, receipt/outstanding calculation, or completion of #60's lifecycle and
broader anomaly acceptance. The existing recording remains an accurate recording of its pinned
older revision; these new scenarios are separate live/local functionality until deployment.

## Issue #60 qualified anomaly correction

The merged implementation adds the ratified qualified-assessment contract and
ADR-026, a hash-pinned synthetic corpus, all eight procurement assessment kinds, explicit
coverage and supersession gates, canonical policy identities, C012-C013 regression challenges,
and a generic append-only lifecycle reducer. The read-only HTTP inspector has source-backed
taxonomy examples plus suppressed, in-review, and resolved projections; caller values cannot
replace fixture inputs and no write route is present. Clean-wheel acceptance includes the corpus,
lifecycle fixture, original order scenarios, new examples, and source drill-down.

The original acceptance evidence is retained in
[`artifacts/issue-60-semantic-evidence.json`](../../artifacts/issue-60-semantic-evidence.json) with
its post-merge findings and historical `not_ready` disposition. The merged correction is recorded in
[`artifacts/issue-60-correctness-semantic-evidence.json`](../../artifacts/issue-60-correctness-semantic-evidence.json): assertion-first
line reconciliation, assessment-context-bound anomaly identity, symmetric schedule supersession,
and C014-C016 known-bad rejection. Adjacent review, relationships, forecasting, costing, and
decision support remain under #41, #44, #61, #52, and #65.

## Demo corpus execution — 2026-10-03

The owner approved the [corpus design](../superpowers/specs/2026-10-03-procurement-demo-corpus-design.md)
and [execution plan](../superpowers/plans/2026-10-03-procurement-demo-corpus.md). Work began on
`codex/demo-corpus-pilot`, primarily #29 (part of #12/#27/#71). PR #175 now contains four projects, 24 source workbooks, 960 row occurrences and 48 structured
HTTP evaluation cases, extending the first one-project increment. Independent original-source
audit and evaluator regression checks are recorded with the branch.
This is branch work, not acceptance on `main`; agent and retrieval milestones remain open.
See [ADR-027](../adr/027-synthetic-corpus-admission.md) for the admitted-input boundary.

First-increment execution, restored public-release identity, and acceptance boundaries are recorded
in [the execution note](procurement-demo-execution-2026-10-03.md).

## G2 run/event foundation — 2026-10-03

`codex/review-agent-run-contracts` is stacked on PR #175's four-project corpus commit.
The foundation implements application-issued run/thread identities, immutable reproducibility
metadata, a scoped SQLite audit ledger and trajectory completeness checks under #70/#68/#72.
The local CLI demonstrates owned resume across process lifetimes. Read the
[run contract](../product/review-agent-run-contract-v1.md),
[ADR-028](../adr/028-application-owned-review-agent-runs.md) and
[foundation plan](../superpowers/plans/2026-10-03-review-agent-run-foundation.md).

This is branch work. Typed corpus tools, model/graph orchestration, exact-brief approval,
idempotent brief saving and live walkthrough acceptance remain subsequent G2 work. Existing
ADR-014 review previews remain non-persistent and do not confer new save authority.

## G2 audited corpus tools — 2026-10-03

`codex/audited-corpus-agent-tools` is stacked on PR #176. Two tools call the existing scoped
investigation/source services and record actual starts, result snapshots or closed typed failures.
Their DTOs share the HTTP serializers. Model arguments cannot supply identity or permissions.
The fixture CLI demonstrates create/investigate/source/finish across processes; these traces
remain excluded from live inference counts. Read the [tool contract](../product/corpus-agent-tools-v1.md)
and [acceptance record](corpus-agent-tools-evidence.md). #66 remains open/In Progress; serial
model orchestration, exact-brief approval/save and live acceptance remain subsequent G2 work.

## G2 exact-brief review/save branch — 2026-10-03

`codex/exact-brief-approval` continues PR #177 for #67/#68. Application-owned immutable
core-fact briefs, exact approval/rejection receipts and atomic single-result saves remain
independent of graph checkpoints. See [ADR-029](../adr/029-exact-brief-review-and-idempotent-save.md),
[the contract](../product/exact-brief-review-v1.md) and
[the execution plan](../superpowers/plans/2026-10-03-exact-brief-approval.md). A separate fixed
human CLI exercises process restart; runtime agent permissions cannot review/save.
Model drafting, graph interrupts, authenticated browser controls and live acceptance remain
subsequent work; this branch does not change main or the public release.

### G2 local fixture browser review branch — 2026-10-03

#74 (M9), part of #53/#67/#68/#70: authenticated loopback transport over the existing exact
review workflow, bounded owned run discovery, scoped source cells and persisted application
timeline. Stacked on PR179. See [the public contract](../product/local-browser-review-v1.md)
and [acceptance boundary](../project/local-browser-review-evidence.md). HTTP and installed
process evidence are distinct from real browser accessibility/interaction, deployment and live
model acceptance; these broader gates remain open. Main and public deployment unchanged.
