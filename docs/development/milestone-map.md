# Delivery milestone map

GitHub milestones are the canonical delivery taxonomy. Historical vertical implementation sequence labels use `S` so they cannot be confused with milestone identifiers.

## Canonical GitHub milestones

| Milestone | Capability | Repository evidence | Status boundary |
|---|---|---|---|
| M0 | Engineering and architecture harness | CI, `AGENTS.md`, typed error codes, ADR-021, checked-in coverage ratchet, C001-C011 | In progress until Issue #3 and harness-hardening sub-issues satisfy acceptance |
| M1 | Synthetic documents and structure/mapping | XLSX adapter, fixtures, contract tests | In progress; Issue #7 remains authoritative |
| M2 | Assertion ledger and provenance | assertion ledger and execution provenance | In progress; milestone state lives in GitHub |
| M3 | Entity resolution | conservative resolver and retained decisions | In progress; broader acceptance remains issue-driven |
| M4 | Reconciliation and governed state | explicit policy, retained decisions, governed expected/observed state | In progress; Issue #15 closed through PR #161; other M4 work remains |
| M5 | Evidence-first UX | chat, inspector, source/review context | In progress; Issue #8 remains open |
| M6 | Retrieval | rebuildable lexical projection lifecycle | In progress; follow-on adapters/evaluation remain open |
| M7 | Intelligence | evidence-backed anomaly taxonomy/orchestration | In progress |
| M8 | Agent tools and guarded workflows | planned issue slices | Planned |
| M9 | Integrated public demo | public synthetic release and bounded recorded walkthrough | In progress; full integrated acceptance remains open |

## Historical implementation slices

| Slice | Delivered capability | Primary evidence |
|---|---|---|
| S0 | Initial repository scaffold | PR #1 |
| S1 | Synthetic XLSX BOM vertical slice | PR #77 |
| S2 | Evidence contract | PR #79 |
| S3 | Claims/evidence application service | PR #80 |
| S4 | Constrained chat routing | PR #81 |
| S5 | Local HTTP inspector | PR #82 |
| S6 | Durable identifiers, source viewer, review context | PRs #86, #88, #90 |
| S7 | Ledger, state, anomalies, and execution provenance | PRs #92, #94, #105, #108 |
| S8 | Retrieval projection foundation | PR #101 |
| S9 | Guarded actions and integrated evaluation | Not delivered |

## Status rules

- A merged slice does not complete a GitHub milestone by itself.
- `Complete` requires implementation, layered tests, documentation, and issue acceptance evidence on `main`.
- Update GitHub Issue, milestone, Project, and this map together when state changes.
- Do not infer milestone status from branch names, PR numbers, or historical slice labels.

## Ratified horizontal domain-platform workstream

This workstream cuts across the existing M0-M9 delivery taxonomy; it does not create a competing milestone scheme. [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md) and [the architecture specification](../architecture/domain-package-and-stage-planning.md) define the contract.

| Step | Primary milestone alignment | Deliverable | Acceptance boundary |
|---|---|---|---|
| Platform contracts | M0 Engineering and architecture harness | Ratified stage definitions, fixed meta-schema, neutral modes, reusable semantic/strategy contracts, dependency rules, and conformance/versioning rules | Stage contract ratified by M0.33; compiler delivered by M0.34; ownership correction delivered by #149 / PR #150; complete typed topology and contract registry delivered by M0.36 / #151 / PR #152 |
| Procurement extraction | M1-M4 semantic pipeline | Procurement package, BOM/BoQ/PO records, source profiles, policy/config refs, and evaluation refs | Initial BoQ/PO pressure-test records were delivered by Issue #149 / PR #150; complete package extraction still requires no observable semantic or provenance regression |
| Compiler and manifest | M0 Engineering and architecture harness | Deterministic compiler, validator, manifest hash, compatibility tests under `platform/domain_packages` | Delivered by M0.34; equivalent authoring data yields byte-equivalent canonical JSON |
| Runtime loading and planning | M9 Integrated demo | Implementation descriptors, capability validation, runtime config, physical plan, semantic trace | No domain-name branching; incompatible implementations fail closed |
| SME/MCP authoring | M8 Guarded agent tools | Schema-aware declarative authoring and validation interfaces | Import remains side-effect-free; writes are reviewable and policy constrained |
| Second-vertical proof | M9 Integrated demo | Another domain package plus shared conformance and swap benchmarks | Demonstrates reuse without changing platform topology for domain convenience |

Implementation issues and Project items must be created and reviewed before these steps are treated as scheduled work. This documentation change is part of the M0 domain semantic-model decision record and does not mark any step complete.

The merged bounded M7/#60 inspector slice compares synthetic order quantity with the governed
requirement and retains both source rows; missing/unresolved cases abstain. Issue #60 is complete through PR #174. Its merged correctness fixes harden the eight qualified assessment kinds, canonical
policy evidence, append-only lifecycle projection, real HTTP source drill-down, and clean-wheel
acceptance. The corrective slice covers assertion-first PO-line reconciliation, assessment-context
anomaly identity, and superseded required schedules. M7 remains in progress for forecast and
decision-support work. See [the comparison contract](../product/showcase-order-comparison.md) and
[qualified assessment contract](../product/anomaly-assessment-v1.md).


### Four-project demo branch — 2026-10-03

PR #175 (`codex/demo-corpus-pilot`, part of #29/#12/#27/#71) expands to 24 workbooks,
960 source-row occurrences and 48 oracle-bound structured HTTP cases. This is branch work,
not `main` or public deployment. See the [execution record](../project/procurement-demo-execution-2026-10-03.md).
Natural-language agent acceptance and retrieval quality remain G2/G3 work.

### G2 run/event foundation branch — 2026-10-03

#70 (M8) is the primary issue for the `codex/review-agent-run-contracts` continuation,
part of #68/#72. Run/event persistence and completeness scoring precede graph construction;
see [the contract](../product/review-agent-run-contract-v1.md). This branch is stacked on
PR175; neither branch is described as merged or live acceptance.

### G2 audited corpus tools branch — 2026-10-03

#66 (M8), part of #53/#70/#72: two actual corpus-service tools with strict arguments, scoped
source lookup, positive invocation/snapshot evidence and typed admission failures. Stacked
on PR176; branch acceptance includes real CLI processes, clean wheels and unchanged structured
HTTP outcomes. See [the acceptance record](../project/corpus-agent-tools-evidence.md).
This does not complete model orchestration, exact-brief approval/save or live-agent evaluation.

### G2 exact-brief review/save branch — 2026-10-03

#67 (M8), part of #68/#53/#72: immutable deterministic briefs, exact receipts, active-version
invalidation, expiry and transactional idempotent saving under ADR-029. The local human CLI
is separate from runtime permissions. Graph recovery, browser review and live-model acceptance
remain open; no broader Issue or milestone completion is inferred.

### G2 fixture serial checkpoint branch — 2026-10-03

#53 (M5), part of #68/#70: optional LangGraph runtime behind an owned port, serial exact
review interrupt, durable receipt/result authority and process-recovery tests. Stacked on
PR178. See [the contract](../product/serial-review-workflow-v1.md). Typed fixture input is
an intermediate gate; model interpretation, browser controls/streams, live evaluation and
broader routing/retry acceptance remain open.

### G2 local fixture browser review branch — 2026-10-03

#74 (M9), part of #53/#67/#68/#70: authenticated loopback transport over the existing exact
review workflow, bounded owned run discovery, scoped source cells and persisted application
timeline. Stacked on PR179. See [the public contract](../product/local-browser-review-v1.md)
and [acceptance boundary](../project/local-browser-review-evidence.md). HTTP and installed
process evidence are distinct from real browser accessibility/interaction, deployment and live
model acceptance; these broader gates remain open. Main and public deployment unchanged.

## Local Qwen intent increment (unmerged branch)

M5/#53 now has bounded natural-language routing on `codex/local-qwen-interpretation`, stacked on PR #180. The local loaded model proposes intent; application-owned journals and existing tools/checkpoints/receipts own evidence and save authority. Nine repeated development CLI walkthroughs and four abstentions passed; see [execution evidence](../project/local-qwen-review-evidence.md). M9/#72 is being evaluated, not completed on main. Full G2 pilot, browser/deployment and held-out quality remain open; expansion continues to depend on G2.

### G2 frozen pilot evaluation branch — 2026-10-03

M9/#72: `codex/g2-pilot-evaluation` evaluates PR181 runtime without model/prompt changes. Installed structured HTTP 48/48 and 464 source checks passed; live intent targets 41/48 with seven unexpected abstentions. The 21 accepted investigations matched facts/recovered/saved once; no false factual answers observed. See [retained evaluation](../project/g2-pilot-evaluation.md). Full G2 is not ready; development interpretation and new frozen evaluation precede expansion. Branch work, unmerged/undeployed; browser release acceptance remains open.


## Intent development continuation — 2026-10-04

Primary M5/#53; Part of #72/#70, stacked on unmerged PR182. Read-only requirement governance and
approval-applicability intents are explicit, with unchanged policy/quantities/human authority.
Installed development regression46/48 versus historical41/48; controls18/20 with safe boundary
abstentions retained and rejected unsafe candidate preserved. All original split cases are now
inspected development data. See [durable experiment](../project/intent-contract-development.md).
Fresh independently authored evaluation, full G2/browser/accessibility/deployment and tiny-fixture
live acceptance stay open. Four projects/24workbooks/960source rows remain; no B2 expansion.

### Real browser review acceptance branch — 2026-10-04

#74 (M9), part of #53/#67/#68/#72/#73: actual clean installed browser source/review/restart
walkthrough, credential-free wide/narrow screenshots and application ledger reconciliation.
Three fixture and 14 authored live submissions pass; selected focus/reflow defects corrected.
Stacked on PR183, unmerged. See [acceptance and remaining gates](../project/browser-live-acceptance.md).
Held-out evaluation, tiny-fixture live routing, full G2 and deployment remain open; no expansion.

### Original source live review branch — 2026-10-04

#71 (M9), part of #53/#66/#67/#68/#70/#72/#74: three original source sets preserve
January GPU-A policy/evidence identities through live intent and exact review. Nine authored
installed browser trials pass with nine calls, eighteen source/tool checks, three restarts and
eight saves. [Evidence and limits](../project/original-showcase-live.md). Stacked on draft PR184,
unmerged; no new data. Held-out quality, full G2 and deployment remain open before expansion.

### Fresh language evaluation branch — 2026-10-04

#72 (M9), part of #53/#70/#71; stacked on draft PR #185. New independent language23/24:
validation 11/12, test 12/12; root development 24/24. Total 47/48 with one valid Cinder cutoff
query safely unsupported. Installed gold48/48 / 464 source checks;48 calls, 54 tool starts, 27 saves.
[Evidence and limits](../project/fresh-language-evaluation.md). Runtime/source facts unchanged.
Now inspected language data; no tuning/retry or full G2/deployment/expansion acceptance.

## Cutoff intent development branch — 2026-10-04

Primary #53/M5, part of #72 and existing authority/run Issues. Stack on #186; unmerged.
A measured prompt clarification distinguishes matching review-cutoff metadata from writes.
Baseline25/28 and candidate26/28 controls retain all failures; candidate inspected-language
regression48/48 and original browser9/9 pass.113 calls/124 tool starts/36 saves, unchanged numeric
policy/sources; old cohort retired. [Evidence/limits](../project/cutoff-intent-development.md).
Global not_ready, broader Issues open, fresh evaluation/release/deployment/expansion gated.


## Fresh language v3 candidate evaluation branch — 2026-10-04

Primary #72/M9, part of #53/#70/#71; stacked on draft #187, unmerged. Frozen cutoff candidate
passes new wording 48/48 (root 24, independently authored validation 12/test 12). Installed 48 gold
and 464 source checks;48 terminal calls, 56 tools, 28 saves; one attempt each, no tuning/retry.
[Evidence and remaining gates](../project/fresh-language-v3-evaluation.md). Expanded seven-file
question lineage preserves historical version2. Source/gold/runtime unchanged; known correlation
prevents source/statistical/causal claims. Full G2 adversarial/release, comprehensive accessibility,
deployment and B2 expansion remain open; four projects/24 workbooks/960 source rows unchanged.

## Installed G2 adversarial acceptance branch — 2026-10-04

Primary #72/M9, part of #53/#66/#67/#68/#70/#71/#74. `codex/g2-adversarial-acceptance` stacks
on draft #188, unmerged. Nine installed HTTP/process failure guards pass with five real and three
controlled terminal attempts, seven tools/one expected failure, three receipts and one exact crash-
recovered save. Missing causal/ownership evidence blocks acceptance. [Evidence and limits](../project/g2-adversarial-acceptance.md).
No runtime/source/prompt/package changes. Full G2/release consolidation, comprehensive accessibility,
deployment and B2 source expansion remain open; four projects/24workbooks/960rows unchanged.

## G2 installed evidence consolidation branch — 2026-10-04

Primary #72/M9; stacked on #189, unmerged. Six hash-bound report populations remain separate:
fresh48/48, original9/9, adversarial9/9, prior controls25/28, candidate26/28 and installed structured
48/48/464source checks. New baseline median investigation HTTP0.168s; fresh interpretation1.158s
is a different task/timing scope, not a speed comparison. [Dossier/remaining gates](../project/g2-acceptance-dossier.md).
Zero new inference; current four-project source corpus unchanged. Full G2/release/browser/accessibility,
measured presentation, main integration, deployment and B2 remain open; broader Issues InProgress.

## Installed browser error recovery branch — 2026-10-04

M9/#74: `codex/browser-error-recovery`, stacked on draft#190, corrects observed draft-loss,
private-error and late-after-lock defects. Actual installed Chromium9/9; fixture5runs/10tools/1save,
zero inference. C018-C020 reject known-bad changes. [Evidence](../project/browser-error-recovery.md).
UI application hash changed; previous G2 reports stay historical. Current-version live acceptance,
measured rehearsal, comprehensive accessibility, main/deploy and full release/B2 remain open.
