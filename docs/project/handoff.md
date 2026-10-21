# Project handoff

## Proposed completed planned-prefix archive - 2026-10-21

Decision #228 (M2, parent #37) proposes the next core increment after PR #227/main8e72f87:
atomically retain the actual planned-prefix receipt with existing source snapshots/bytes,
then support exact scoped restart reads without executors or source access. Proposed ADR-044
and the [written design](../superpowers/specs/2026-10-21-planned-prefix-archive-design.md)
specify first-retention semantics, an additive storage capability and preservation of every
legacy caller. This is a proposal awaiting owner review; no runtime implementation is authorized
or delivered by these docs. Wider execution and general jobs/recomputation remain separate.
The same-baseline post-merge advisory39691201487 succeeded with a valid bounded Gemini report;
direct tracker reconciliation updated M9/#12 priority and #109 closed-child checkboxes.
The duplicate ADR-033 numbering remains a separate documentation follow-up.

## Actual explicit planned execution prefix - 2026-10-21

Feature #226 (M9, parent #12; approved decision #225/ADR-043) connects full planning to actual
synchronous BOM INGEST-through-ASSERT execution through an explicit runtime registry. The
[public contract](../architecture/package-execution.md) retains typed payloads, shared source/
scope/lineage guards, resolved declaration/instance/content identities and real producer events.
All twelve declarations remain visible; later entries are NOT_EXECUTED, including unvisited EMPTY
declarations. Prefix completion is distinct from package completion. Existing planner and legacy
BOM/archive/review/replay callers remain separate and compatible. No durable attempt journal,
result cache, neutral executor, governing state, general recompute, authority or deployment is added.
Broader #12/#7/#20/#35/#36/#75 remain open. Pre-slice advisory39671302454 on baseline07d089b failed
Gemini503; deterministic Project audit/direct review are separate. The M9 description's historical
demo-priority wording is recorded drift, not authority to resume demo work.

## Explicit selected-review source-SKU replay - 2026-10-21

Issue #223 (M2, parent #41; approved policy #222/ADR-042) adds a separately invoked
[reviewed view](../domains/procurement/reviewed-source-sku-query.md). Actual row applications consume
source assertions and validated approved-correction data roots; the set producer consumes at most32
original/reviewed row references. Explicit approved_correction_roots/v1 initialization adds capability
tables beside unchanged archive1/review1/dependency1 records. Missing capability/evidence fails closed.
Exact scope/as-of/selection/context retries retain the first receipt; null remains unresolved, selected
conflicts fail and original source/query values remain unchanged. No latest winner, canonical/governing
state, global freshness, automatic scheduler or result cache. Spec/plan retain the policy and delivery
contract. Broader #13/#35/#37/#41/#46/#48/#56/#63 remain open. Pre-slice advisory39657670491 on
main `a26d615` failed Gemini HTTP503; deterministic Project audit/review is separate evidence.

## Actual archived source-SKU producer adoption - 2026-10-21

Issue #220 (M2, parent #35, part of #13/#37/#41) executes a real source-local distinct-SKU
producer from the immutable archive and registers its actual input/event/output reference through
the existing dependency port. [Contract](../domains/procurement/archived-source-sku-query.md), ADR-041
and spec/plan preserve source strings versus canonical identity, unresolved null/partial-known
sets, exact source/context retries and original evidence. No schema or old wire shape changes.
Values are replayed from original source, not materialized in a new query-result cache. Approved
SKU correction impact now identifies a real executed query reference; approval still changes no
source/query/governed state. Local manifest metadata is caller-pinned, not production attestation.
Broader #13/#35/#37/#41/#48/#56 remain open; next is explicit controlled invalidation/recomputation
and further governed/state producer adoption. Pre-slice advisory39597750624 at main82c73cf failed
Gemini503; deterministic Project audit was reviewed separately. No successful provider report.

## Declared downstream dependencies and correction impact - 2026-10-20

Issue #218 (M2, parent #41, part of #35/#37/#13) adds immutable dependency declarations and
read-only impact over an exact approved correction. [Contract](../architecture/correction-impact.md)
and ADR-040 distinguish caller-supplied producer receipts from verified execution and global
consumer coverage. Explicit additive dependency schema1 leaves archive1/review1 unchanged.
Bounded traversal retains shared paths and exposes omitted frontier; empty results never mean
all consumers are unaffected. No source/state mutation, automatic recomputation or operational-agent
authority is added. Broader #13/#35/#37/#41/#56/#63 remain open. Next is real downstream producer
adoption, followed by explicit policy for controlled invalidation/recomputation. Latest pre-slice
advisory run39514129070 at main8bb6dda failed Gemini503; deterministic Project audit was reviewed
separately. No successful provider report or production execution is claimed.

## Document-value correction/review lineage — 2026-10-20

Issue #216 (M2, parent #41, part of #37/#13) adds evidence-bound immutable document-value tasks,
exact-digest human decisions and separate accepted-correction records behind a journal port.
[Public contract](../architecture/document-review.md) and ADR-039 retain original source values,
scoped/as-of history, stable retries/conflicts and prospective review time. Accepted corrections
signal recomputation required with downstream discovery not evaluated; no governing state or source
assertion is rewritten. Explicit additive Postgres init leaves archive schema1 intact. The separate
trusted human CLI does not grant operational agents REVIEW permission or production authentication.
Broader #13/#37/#41 stay open for other review workflows, downstream traversal/recomputation and
policy integration. Latest pre-slice advisory audit39497397461 at main1bf87ac failed Gemini503;
Project and deterministic planning audit were reviewed separately. No successful advisory report.

## Durable Postgres assertion archive — 2026-10-20

Issue #213 (M2, parent #37, part of #13/#35/#36) adds atomic materialization of the complete
five-stage source snapshot and captured bytes behind a neutral port. [Archive contract](../architecture/assertion-archive.md)
and ADR-038 define explicit init, scoped restart reads/export, stable exact retry, conflict retention
and typed integrity failures. The optional storage driver stays outside core semantics; the default
BOM modes and legacy in-memory ledger remain compatible. This is a trusted local developer boundary,
not production deployment or queue exactly-once processing. Broader #13/#35/#36/#37 stay open; next
is explicit correction/review lineage under #37/#41. The pre-slice advisory audit failed Gemini
HTTP 503 (run 39443547796); no successful report is claimed. Project and deterministic planning
audit were reviewed separately; known #109 checkbox drift and duplicate ADR-033 remain separate.

## BOM source assertion adoption — 2026-10-20

Issue #211 (M1, parent #33) extends the concrete BOM caller to five stages with `--assertions`
and explicit normalization policy. [Contract and continuation](../domains/procurement/bom-assertions.md)
and ADR-037 record additive SourceAssertion context, upstream event identity, unresolved nulls,
raw evidence, distinct conflicting rows and source-SKU-only mentions. Legacy assertion IDs and
three/four-stage modes remain compatible. Null without unresolved context is rejected (C030).
This slice emits claims and mentions without resolution, authority selection or CLI persistence.
#33 remains open; next is durable ledger/content/replay semantics against #13/#35/#37. The general
physical planner remains separate. Main's pre-slice roadmap audit succeeded on 32b1788 in
[run 39430341581](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/39430341581).
Its historical-demo narrative finding is qualified by the explicit supersession notice below;
#109 checkbox drift and broader #120/#121 acceptance require separate stewardship.

## Explicit BOM normalization — 2026-10-19

Issue #209 (M1, parent #31) adds a procurement NormalizeStrategy to the existing shared-stage CLI
with explicit `--normalization-policy` input. [Contract and continuation](../domains/procurement/bom-normalization.md):
quantities become exact Decimal each, prices retain declared currency/denominator, raw source
fields/evidence remain available, and missing/unmapped values stay unresolved. Source-row hints
preserve duplicate/missing SKU rows. The fourth transformation records policy/provenance and an
empty batch receipt when appropriate; no assertion or authority selection is performed. Default
three-stage behavior and the legacy demo remain compatible. #31 stays open for broader normalization;
next is source-assertion adoption under #33, followed by durable ledger/content/replay work.

## Shared BOM stage adoption — 2026-10-19

Issue #207 (M1, parent #7) adds concrete capture/structure/mapping strategies and an installed
`interfaces.bom_stages` caller. [Contract and continuation](../domains/procurement/bom-stage-adoption.md):
exact captured bytes survive mutable source changes within a process; generic XLSX structure keeps
cell coordinates; procurement mapping retains raw values and missing/unmapped diagnostics. Three
real transformations retain source and component provenance. Nine hash-pinned synthetic BOMs match
row/cell/raw-field expectations (1,608 fields). Legacy paths retain shared cell mechanics and C002.
This is not a general plan executor, durable store or normalized/asserted procurement pipeline.
Issue #209 adds the bounded normalization path below #31; ASSERT adoption against #33 and broader
normalization remain separate, followed by durable ledger/content/replay work.

## Runtime package planning — 2026-10-19

Issue #205 adds platform-owned immutable implementation descriptors, strict JSON registry/TOML
configuration loading, capability/contract/version checks and deterministic physical planning.
The installed `interfaces.plan_package` CLI accepts an explicit compiled manifest, registry and
config; [runtime contract and acceptance](../architecture/runtime-planning.md) describe its hashes,
typed failures and twelve retained logical stages. Procurement and non-procurement fixtures use
the same path. Fixtures advertise compatibility only; no executor, service-health proof, source
validation, semantic execution trace, policy loading, materialization or action authority is added.
Next: adapt real procurement services to universal stage contracts with source/evidence acceptance,
then durable ledger/replay. Broader M0–M9 and demo/release acceptance remain open.

## Core architecture resumption — 2026-10-19

The owner has resumed core architecture work after the demo integration. Issue #201
adds the first real procurement DomainPackage, domain-owned BOM source schema and
installed canonical-manifest command; see [package contract](../domains/procurement/package-v1.md).
This is an initial declaration/adoption slice. Full procurement stage adaptation and execution remain subsequent work;
Issue #205 supplies registry/capability validation and physical planning separately;
EXECUTE bindings are requirements, not runtime availability claims. Demo acceptance
and broader M0–M9 criteria remain separately tracked. The audit repair is merged in
PR #200 and the main-branch hosted audit passed at `f4d8145` (run 39340032790).

## Roadmap audit recovery — 2026-10-19

Issue #199 replaces the quota-exhausting Gemini agent loop with one explicit-model,
read-only evidence-snapshot request. See [ADR-036](../adr/036-bounded-roadmap-review-request.md)
and [recovery evidence](roadmap-review-recovery.md). The bounded scope excludes PR
bodies and source-code inspection; broader Project/pagination work remains #117.
This repair does not change procurement architecture delivery priorities.

## PR reconciliation — 2026-10-05

PR #193 merged the complete #175–#192 demo chain and its corrective review pass to `main`
at `d3aea05c5e81890afc316ee4fc6f1a2c88b0544d`. Every current required check passed, including
coverage and the revision-bound PR contract. The ancestor PRs contain no remaining unique work;
their historical evidence remains available. The sections below record the original branch-time
acceptance and are historical where they describe this chain as unmerged.

The remaining integration reconciles #172 host routing and #157/#159 dependency updates against
that main revision. [ADR-035](../adr/035-development-agent-host-routing.md) records the host-role
boundary and resolves #172's missing-decision-record finding. The aggregate baseline CLI test
now allows 600 seconds for its unchanged 48 investigations and 464 source lookups: GitHub's
previous 180-second timeout killed the correctness run despite 88.94% measured coverage.
The report still records every request's latency; no product performance threshold is changed.
Human timing, current-build live
inference, deployment, full G2/release, and B2 remain open; broader Issues remain in progress.

## Evidence-focused demo story and source highlighting — 2026-10-05

`codex/demo-integration-review-fixes` now adds an analyst-first, exact-scope reconciliation review
on top of the evidence-focused reviewer and eight-slide editable native deck. The review presents
the discrepancy and highlighted admitted sources before technical run history. An authenticated
analyst may choose one of exactly two eligible requirement revisions, keep the item unresolved,
or flag the assessment for correction with a rationale. A governing choice applies only to the
exact tenant/project/site/item scope from its server-owned effective time; it never rewrites an
earlier assessment, discards the losing assertion, or triggers a purchase or external action.
ADR-034, the public contract, and C028 record those boundaries. The replacement 30.72-second
recording demonstrates the new resolution flow with character-by-character typing and both
conflicting BOM sources highlighted.
The deck now
shows the complete source-to-action architecture vision, gold data at every boundary, human
governance at controlled checkpoints, and the current implementation boundary. Findings open
the first citation automatically; selectable evidence cards expose selection state; original row
cells highlight supporting columns; governing-authority JSON remains fully inspectable. The
The prior recording shows paced typing and changing Who/What/Why/How/When explanation before a human rejects
an unresolved conflict. [Deck](demo-storytelling-deck.md), [recording and limits](demo-rehearsal.md),
and [compact results](demo-storytelling-results.json).

Latest local verification: focused reconciliation/reviewer checks passed; full `make check`
passed 790 tests with 22 explicit opt-in skips and 88.94% coverage; package smoke passed; all 28
known-bad challenges were rejected. The current public browser recorder completed one fixture
submission and exact-scope reconciliation. The prior PR #193 coverage failure was a 180-second timeout in the baseline
CLI test at older head `b3afe828`; it was not a coverage-threshold failure. The same full local suite
now completes in 409.84 seconds. One current live recording attempt returned `model_unavailable`
with port 8000 offline and was not retried; publishable media is explicitly fixture/no-model.
No merge or deployment. Current-build live inference, human timing, full release and B2 remain open.

## Demo integration review corrections — 2026-10-04

`codex/demo-integration-review-fixes` is based on draft #192. Eighteen demo PR heads form a
linear chain and all ten required checks passed at each inspected head, but six automated review
threads on #176–#178 remained unresolved. This candidate fixes failure/non-applicability accounting,
terminal chronology, run/brief CLI build fingerprints, tool payload validation, completed-save
replay after replacement and vanished-item error mapping. [Contract, audit and verification](demo-integration-review-fixes.md).
Independent review found two further gaps; the root corrective pass adds active-ledger integrity
and complete shared payload validation ([ADR-033](../adr/033-validated-application-payloads.md)).

No merge, deployment, inference or corpus change. Prior live walkthroughs retain their original
application identity; changed runtime requires a separate current-version live check. Integration
must include these corrections; older branches remain unsafe to release independently. Human timed
rehearsal, full G2/release and deployed acceptance remain open; B2 stays gated.

## Current-version demo rehearsal artifacts — 2026-10-04

`codex/demo-rehearsal-recording` stacks on draft #191. The unchanged installed current app passes
one 14-submission local Qwen development walkthrough: 14 calls/20 tools/108 source checks/8 saves.
A [captioned five-minute fixture screenshot replay and operator script](demo-rehearsal.md) show
mismatch, exact/repeated save, unresolved rejection and missing observation. It is not continuous
screen recording or timed human rehearsal; fixture media and live evidence remain separate.
Runtime/prompt/source/gold unchanged. Next: actual human timed rehearsal, deliberate stack integration
and separately authorized deployment. Full release/B2 remain open; prior held-out evidence is historical.

## Installed browser error recovery — 2026-10-04

`codex/browser-error-recovery` stacks on draft #190, unmerged/undeployed. Twelve actual clean-installed
Chromium cases pass: failed replacement retains the prior exact brief, private failure fragments
stay out of UI, locked callbacks issue no late history request, and lost save acknowledgment
recovers the same single durable result. Eight fixture runs/sixteen tool starts/one save/zero inference;
live-page error checks intercept ask before backend. [Evidence and limits](browser-error-recovery.md).
The changed page changes the application hash; prior G2 passes remain historical, not current
live acceptance. Full G2/release/accessibility, measured rehearsal, main integration/deployment and
B2 remain open. Next: bounded reviewer rehearsal and separately scoped current-version live check.

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

## Named agent roles

- **`mac-planning-agent`** — Mac-hosted planning and review role. It handles architecture review,
  cross-repository sequencing, issue decomposition, acceptance design, and evidence planning. It
  is the preferred planning surface when the needed model is available there. Verify current
  model availability when choosing a host. It does not implement product code or
  run the implementation delivery loop.
- **`dgx-implementation-agent`** — DGX-hosted implementation role. It owns all implementation
  changes, including source, tests, documentation, packaging, CI, benchmarks, deployment changes,
  verification, and PR preparation, in an isolated checkout.

The Mac role hands off a bounded plan with its governing Issue, source revision, touched contracts,
acceptance examples, evidence requirements, and unresolved decisions. The DGX role re-grounds that
plan against the current checkout and authoritative artifacts before changing anything. The
handoff is planning input, not implementation or release authorization. Explicit owner instructions
may select another host or authorize integration/merge work; see [ADR-035](../adr/035-development-agent-host-routing.md).

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
