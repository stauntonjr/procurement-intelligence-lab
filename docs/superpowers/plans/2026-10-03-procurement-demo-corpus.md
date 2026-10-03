# Procurement Demo Corpus Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use subagent-driven-development only if the owner selects delegated execution. Checkboxes track verified completion, not intent.

**Goal:** Deliver a richer, source-backed procurement investigation through the live review agent, then expand into a measured retrieval benchmark.

**Architecture:** Preserve legacy fixtures and routes. Add a versioned synthetic corpus adapter behind a read-only port, a scoped investigation service over existing policy services, and evaluator-only gold artifacts. The operational agent consumes the same service as the public caller.

**Tech Stack:** Existing Python 3.12–3.13, stdlib dataclasses/Decimal/JSON/ZIP/XML, pytest and uv; existing HTTP inspector. Optional model/orchestration dependencies remain governed by #53/#70.

**Spec:** [Corpus design](../specs/2026-10-03-procurement-demo-corpus-design.md).

**Implementation reference:** [LangChain Academy study](../../langchain-ref/README.md), especially
the [Issue mapping and acceptance checks](../../langchain-ref/procurement-application.md).
Use these for graph state, review/recovery and evaluation mechanics; they do not change domain
authority or count as executed acceptance evidence.

## Global constraints

- Preserve existing golden artifacts, IDs, hashes and legacy response semantics.
- Runtime packages must not include gold answers, qrels, split-purpose labels, or oracle-only case descriptions.
- Search returns candidates; the assessment service resolves the complete admitted scoped item/revision inventory before evaluating.
- Missing observations have insufficient coverage and yield not-assessed; they do not establish missing PO.
- Domain values use stdlib dataclasses and Decimal; external mechanics remain behind a Protocol.
- Application-owned run identity, audit events and review/save records remain independent of optional LangSmith export and graph checkpoints.
- Evaluation distinguishes pass, fail, unknown and not-applicable; missing required events cannot count as success. Synthetic/replayed traces are excluded from live metrics.
- No training, model-provider provisioning, GPU allocation, public-data download or external procurement actions are authorized by this plan.
- Every semantic slice follows semantic-change-loop, tests the real caller, records latest-revision evidence and gets fresh review. Runtime resources require a clean-wheel check.

## Review focus

1. Same item identifier in another project cannot contaminate assessment or source viewing: Task 3/4.
2. Missing evidence after top-k truncation cannot become zero or missing PO: Task 3/6.
3. Generator and production code cannot silently agree on the same bug: Task 1/5 independent gold review.
4. Duplicate assertion replay and two independent PO lines must produce different aggregation behavior: Task 3.
5. Installed runtime must neither lose nested artifacts nor expose evaluator labels: Task 4/5.

## Delivery sequence and effort

| Gate | Deliverable | Primary issue | Planning estimate |
|---|---|---|---|
| G0 | Roadmap/contract alignment and public-demo diagnosis | #12/#73 | 0.5 focused day |
| G1 | Four-project corpus, audited labels, admission and deterministic HTTP investigation | #29; part of #27/#71 | 2–3 focused days |
| G2 | Existing agent plan consumes corpus service; approval/recovery and live acceptance | #53/#66–#74 | 2–3 focused days |
| G3 | Twenty-project retrieval benchmark, lexical baseline then embedding comparison | #62/#57/#55 | 2–4 focused days |

These are estimates, not deadlines or guaranteed throughput. G0–G2 is a roughly 5–7 day interview
demo target with contingency. G3 follows, rather than delaying a working demo. If only two days
remain, keep the original three-scenario agent scope and label corpus/retrieval work incomplete.
Do not compress by dropping approval, failure or source-integrity gates.

### First executable increment

The owner selected native implementation and independent review. Begin G0 and one project
(six workbooks, 240 source-row occurrences); the four-project counts and split isolation below
remain later G1 acceptance. Preserve exact replay identity; the two order documents contain
independent lines or explicit conflicting assertions, never implicit newest-snapshot precedence.
Source lookup includes both tabular cells and authority sidecar records.

### Refinement after the LangChain Academy study

The corpus sizes and G0–G3 order remain unchanged. Inside G2, use this sequence:
run/event contracts and evaluator checks → one serial agent workflow → exact-brief review and
crash recovery → real-model acceptance → optional LangSmith export. Define evaluation expectations
with the contracts, before implementing the graph. A local application audit is required;
hosted tracing remains optional. These refine existing acceptance, not add another platform.

## File responsibilities

Existing files below were inspected; new paths are proposed and must not be mistaken for shipped code.

| Path | Responsibility |
|---|---|
| `synthetic/specs/procurement-corpus-v1.json` (new) | Source-generation specification, version/seed, project and document facts; no runtime authority by itself |
| `synthetic/specs/README.md` | Corpus purpose, counts, regeneration, evidence limits |
| `tools/generate_procurement_corpus.py` (new) | Deterministic source rendering and runtime manifest construction |
| `src/procurement_intelligence_lab/examples/corpus_v1/` (new) | Packaged admitted artifacts and source-metadata records, excluding evaluator-only data |
| `src/procurement_intelligence_lab/ports/corpus.py` (new) | Read-only corpus port and immutable neutral inventory/request records |
| `src/procurement_intelligence_lab/adapters/synthetic_corpus.py` (new) | Hash/schema/path validation, XLSX loading and scoped artifact lookup |
| `src/procurement_intelligence_lab/application/corpus_investigation.py` (new) | Existing governance/assessment composition for requested item and cutoff |
| `src/procurement_intelligence_lab/interfaces/corpus_http.py` (new) | Boundary validation and DTOs for corpus investigation/source routes |
| `src/procurement_intelligence_lab/interfaces/web.py` | Minimal route dispatch and corpus controls; preserve legacy scenario path |
| `evals/procurement_corpus/v1/` (new) | Splits, query/qrel/gold manifests and gold-review record; never runtime resources |
| `tools/evaluate_procurement_corpus.py` (new) | Reproducible caller-based deterministic/retrieval scoring and per-case results |
| `tools/package_smoke.py` | Installed-artifact checks including nested corpus and absence of gold |

## Task 0: align contract, delivery state and authority

**Issues:** #12/#27/#29/#71/#73. No product code in this task.

- [x] Re-read live Issue bodies, main/PR state, AGENTS, handoff, milestone map and ADR-019/023/024/026. Preserve concurrent work.
- [x] Record the new corpus slice in existing Issues using manage-github-planning; inspect before writes, retain broader criteria, and audit afterward. Identify one primary issue per implementation PR.
- [x] Correct stale #60 status in `docs/project/handoff.md` and `docs/development/milestone-map.md`; link this proposal with its actual approval/implementation status.
- [x] Add an ADR using the next available number for admission, authority records, source lookup, and runtime/gold separation. Ratify it before architectural code changes.
- [x] Diagnose the public 404 under #73 using the documented hosting/runbook. Record the actual cause and pin the restored revision; do not assume a healthy process proves working browser routes.
- [ ] Verify root, health, question submission and original source click on the restored release. Preserve the current service until the new release passes. Commit the documentation/ADR slice through normal PR review.

## Task 1: freeze pilot scenarios and independent gold

**Files:** new generation spec and `evals/procurement_corpus/v1/{manifest,queries,qrels,gold,gold-review}.json`; update `synthetic/specs/README.md`; new `tests/contract/test_corpus_manifest.py`.

**Interface:** JSON schema version `procurement-demo-corpus/v1`; document records carry artifact ID,
project/site, source type, content hash, relative path and evidence-linked applicability metadata.
Query records carry query ID, text, scope, canonical-item expectation, cutoff and category. Gold
records carry exact status/reason/value and valid evidence sets. Gold and split labels are evaluator-only.

- [ ] Write failing `test_pilot_inventory_and_split_isolation`: four projects, six documents/project, forty source rows/document, 48 queries, query counts 24/12/12, no project/revision overlap.
- [ ] Run `uv run pytest -q tests/contract/test_corpus_manifest.py`; confirm the intended missing-contract failure.
- [ ] Author the four project specifications and 48 gold queries with the category counts in the design; use different target identifiers and quantities per project. Keep every target case supported by a hand-checkable source/authority table.
- [ ] Add `test_gold_requires_declared_evidence_roles` and `test_manifest_rejects_unknown_versions_duplicate_ids_and_orphan_labels`; validate declared document/row identities here and actual bytes/locations in Task 2. Require explicit expected failure/clarification where no factual answer is valid.
- [ ] Audit all 48 gold cases independently of production service output. Record source arithmetic, authority interpretation, reviewer and corrections; do not mark this done based on generator tests.
- [ ] Run the contract tests to PASS and commit the reviewed specification/label slice. Generated artifact hashes are filled and revalidated in Task 2.

## Task 2: render and admit actual artifacts reproducibly

**Files:** generator, corpus port, synthetic adapter and packaged directory from the file map;
new `tests/unit/test_corpus_generation.py` and `tests/contract/test_corpus_adapter.py`.

**Interfaces:** generator `generate(spec_path: Path, output_dir: Path) -> Path` returns the runtime
manifest path. Port `CorpusReader.inventory(*, context: RequestContext) -> CorpusInventory` and
`CorpusReader.source(evidence: EvidenceRef, *, context: RequestContext) -> CorpusSourceRow | CorpusSourceRecord`.
`CorpusInventory` is an immutable tuple-backed record of admitted documents, parsed source rows,
and evidence-linked authority metadata. It contains no gold or scenario-answer fields.
Also define neutral `CorpusSourceRecord(collection, record_key, fields)` for authority sidecars.
Define neutral `CorpusSourceRow(sheet: str, row: int, headers: tuple[str, ...],
cells: tuple[str, ...], highlighted_columns: tuple[str, ...])` in the port module; the adapter
maps its existing XlsxSourceRow into that record. The port must not import adapter types.

- [ ] Write `test_generation_is_byte_reproducible`: two independent output directories have identical relative paths and SHA-256 values, including stable ZIP member metadata.
- [ ] Write `test_adapter_reads_actual_xlsx_values`: change a source quantity, regenerate its declared hash, and observe the parsed value change without consulting gold.
- [ ] Write rejection tests for hash tampering, escaping paths, duplicate IDs, missing sidecar evidence, unauthorized scope and unsupported schema version.
- [ ] Run `uv run pytest -q tests/unit/test_corpus_generation.py tests/contract/test_corpus_adapter.py`; confirm intended failures.
- [ ] Implement deterministic rendering with existing admitted column names, explicit source-metadata records and hash verification. Use existing XLSX reader/source-viewer mechanics. Never derive authority from filename order.
- [ ] Generate with `uv run python tools/generate_procurement_corpus.py --spec synthetic/specs/procurement-corpus-v1.json --output src/procurement_intelligence_lab/examples/corpus_v1`; validate final manifest/gold evidence locations.
- [ ] Run both test files and Task 1 contracts to PASS, then commit. Record 960 source-row occurrences separately from unique entities and qualified lines.

## Task 3: investigate by scoped item and time

**Files:** new application service; new `tests/contract/test_corpus_investigation.py`;
existing governance/assessment modules are reused, not rewritten for corpus convenience.

**Interfaces:** immutable `InvestigationRequest(canonical_key: str, as_of: datetime)`;
`CorpusInvestigationService(reader: CorpusReader).investigate(request: InvestigationRequest,
*, context: RequestContext) -> InvestigationResult`. Result carries governed requirement,
qualified quantity assessment, admitted input identities and evidence. Reuse existing domain
result types; do not turn a descriptive GPU substring into canonical identity.

- [ ] Write gold tests for mismatch, match, unresolved requirement and missing observation on development projects; assert exact values, status/reason and evidence roles.
- [ ] Add tests for wrong project, unknown item, empty inventory, exact replay versus independent lines, conflicting duplicates, stale/future evidence and an exact effective-date boundary.
- [ ] Add zero, negative and fractional quantity cases under the existing policy's allowed/invalid semantics; unit conflicts abstain. Document any non-applicable family with rationale.
- [ ] Add `test_distractor_permutation_does_not_change_assessment`, `test_top_k_omission_cannot_prove_absence`, and `test_gold_unavailable_during_investigation`.
- [ ] Run `uv run pytest -q tests/contract/test_corpus_investigation.py`; confirm intended failures.
- [ ] Compose existing governing projection and AnomalyService over the complete eligible corpus inventory. Read values and identities from sources, preserve authority evidence, and return typed absence/conflict. Do not add missing-PO or receipts policy.
- [ ] Run focused contracts and existing `tests/contract/test_showcase_discrepancy.py` and `tests/regression/test_anomaly_assessment_correctness.py` to PASS. Record semantic evidence, fresh review and commit.

## Task 4: deliver the actual public and installed caller

**Files:** corpus HTTP adapter and minimal web dispatch/UI changes; new
`tests/integration/test_corpus_http.py`; update `tools/package_smoke.py`.

**Interfaces:** `GET /api/corpus/investigate?project=<id>&item=<key>&as_of=<ISO8601>`;
`GET /api/corpus/source?project=<id>&evidence_id=<id>`. Server derives scope and permissions
from its configured synthetic allowlist. Client parameters cannot grant scope. DTOs expose
authoritative results, policy and evidence; no gold or expected-answer fields.

- [ ] Write real-server tests for multiple items/projects/cutoffs, source-cell resolution and legacy route compatibility. Assert 403 unauthorized scope, 404 unknown item/evidence, and 422 malformed request; business abstention remains 200 with typed disposition.
- [ ] Add source cross-project denial, tampered-artifact rejection and unsupported identifier tests.
- [ ] Run `uv run pytest -q tests/integration/test_corpus_http.py`; confirm intended failures.
- [ ] Implement thin routes and project/item/date controls with visible scope and uncertainty. Preserve the legacy scenario selector and default inspector.
- [ ] Extend clean-wheel smoke to load nested artifacts outside the checkout and exercise both corpus routes. Inspect wheel members: no gold, qrels or evaluator manifests. Run `make package-smoke` to PASS.
- [ ] Run the HTTP tests and perform browser submission, source drill-down, keyboard use and error recovery. Record actual interactions and revision. Complete semantic evidence/review and commit.

## Task 5: evaluation and live-agent integration gate

**Files:** new evaluator and `tests/unit/test_corpus_evaluation.py`; evaluation artifact under
`artifacts/procurement-corpus/v1/`; agent changes remain owned by #53/#66–#74.

**Interface:** `uv run python tools/evaluate_procurement_corpus.py --base-url URL --manifest
evals/procurement_corpus/v1/manifest.json --split {development,validation,test} --output PATH`.
Results include per-query outcome, evidence-role checks, errors, actual timing/calls and revision.
The evaluator supplies only request inputs to HTTP; it never sends gold to the application.

Execute the following blocks in order. Agent implementation details belong in a bounded
#53/#66–#74 execution plan referencing these contracts; do not implement the entire block as one
unreviewed change.

### 5A: run isolation, observable events and evaluator contracts first

**Contract artifact:** create `docs/product/review-agent-run-contract-v1.md` under #70/#68.
It defines server-issued run ID, authorized scope, graph thread binding, query/attempt IDs,
brief digest, evidence-snapshot ID and idempotency key. Events have stable event ID, causal parent,
run/attempt, tool name/version, actual start/result/error, and execution kind. Correlation IDs
cannot grant authority. Local durable records own review/save state; telemetry mirrors them.

- [ ] Define fresh run/thread state for each independent evaluation example; retries of the same example retain explicitly bound run identity. Reject cross-run/scope resume before checkpoint loading.
- [ ] Define allowlisted public and optional-export event fields. Neither a graph output schema nor a private channel is treated as redaction. Exclude hidden reasoning, credentials and evaluator gold.
- [ ] Add acceptance cases for concurrent example isolation, partial/missing events, unsuccessful tool calls and fabricated completion. Reconcile trace completeness with application records rather than trusting a model-produced message list.

- [ ] Write scorer tests that reject wrong numerical value, correct citation with wrong support, missing required evidence, false confident answer and omitted failed query. Alternative valid evidence sets must score correctly.
- [ ] Add separate trajectory outcomes `pass`, `fail`, `unknown`, `not_applicable`; report all four counts. Required missing/partial events are unknown and block the corresponding acceptance gate. Non-applicable cases do not inflate pass rate. Deduplicate replayed events by stable identity, while checking the durable saved-result count independently.
- [ ] Run `uv run pytest -q tests/unit/test_corpus_evaluation.py`; confirm intended failures, implement scoring, rerun to PASS.
- [ ] Freeze the dataset/model/prompt/tool/application versions before the validation/test run. Preserve all failures and report category/project denominators; do not tune on test output while continuing to call it held-out.
- [ ] Run all 48 pilot deterministic queries through HTTP; require all gold cases and source checks to pass. Execute adversarial transport/scope/integrity cases separately and report them separately.

### 5B: bounded workflow and application-owned review/recovery

- [ ] Adapt #66's tools to CorpusInvestigationService and source lookup; #53 interprets natural language into item/date, asks clarification for ambiguity, and drafts from authoritative fields. Labels/case IDs must not choose the answer.
- [ ] Pin a coherent optional LangGraph/checkpointer dependency set and smoke-test the selected interrupt/resume API before integration. Start with a serial graph, explicit partial updates and bounded steps/model calls/time. Do not copy floating course requirements or process-global thread state.
- [ ] Keep arbitrary SQL and direct database access outside model tools. A successful typed tool result, not a tool-call request or error string, satisfies the inspection prerequisite.
- [ ] Interrupt with a persisted immutable brief reference/digest/snapshot. The authenticated resume boundary records a review decision and supplies its receipt ID; the save service validates the receipt, scope, freshness and exact content. Client `approved=true` is insufficient.
- [ ] Complete #67/#68 exact-brief approval and persistent restart/idempotency checks. Preserve all three original walkthrough outcomes while demonstrating richer evidence selection.
- [ ] Inject a process crash after durable brief save but before graph checkpoint completion. On restart/resume, verify one saved result and the original approval binding. Test rejection, expired/altered approval, checkpoint fork and evidence change; fresh evidence or edited content requires fresh approval.
- [ ] Test event streaming separately from final responses for prohibited fields. If parallel reads are later justified, add unequal-depth fan-in and reducer-delta tests before enabling them; parallel execution is not a first-demo requirement.

### 5C: real-run evidence, release and optional tracing

- [ ] Under the authorized configured model, run three repetitions of each live walkthrough plus failure cases required by #72. Record all runs and enforce the design's release gates. No inference credentials/configuration means live acceptance remains incomplete.
- [ ] Keep replay/fixture runs out of live latency and model-quality aggregates; preserve actual event timestamps. Compare code-based correctness and policy gates before any optional pairwise clarity judge.
- [ ] If #75's tracing time box is used, export only approved allowlisted synthetic events. Verify disabled/unavailable tracing leaves audit, review and save behavior intact. No trace upload or paid judge run is implied by completing local acceptance.
- [ ] Complete #73/#74 clean-install, deployed browser and five-minute walkthrough checks. Run `make check`, `make package-smoke`, affected challenges and latest-revision semantic validation; preserve a labeled recording fallback.
- [ ] Update README, handoff, milestone map and live Project status to verified delivery. Do not close #12/#29/#62 or broader issues solely for this bounded slice. Commit/review each owning implementation slice.

## Task 6: expand only after G2 passes

**Issues:** #62 primary; #57 lexical, #55 embeddings; #59 only if fusion earns further work.

- [ ] Create a separate benchmark implementation plan from pilot errors and the design's B2 targets: twenty projects, 120 documents, 4,800 rows, 200 queries, project split 12/4/4.
- [ ] Add independently authored families and audit gold; deduplicate near-identical questions and record generator lineage. Keep parser/layout expansion separately scoped.
- [ ] Measure the existing lexical projection as a reference; implement exact/BM25 behavior under #57 and compare on the same frozen corpus.
- [ ] Add one embedding adapter under #55 only with an explicit model/resource choice. Compare evidence recall/ranking, authoritative downstream answers, scope/revision failure rates, latency and measured cost. Do not announce a winning method before evaluation.
- [ ] Add regression tests proving scope filtering precedes ranking and stale/top-k candidates cannot become governing state or coverage proof.
- [ ] Make projection/cache identity depend on admitted source hashes and inventory, model and configuration; test deletion, addition and changed embedding configuration, not only modification timestamps. Compare retrieval-unit sizes on the frozen evaluation set before choosing row/section/document context.
- [ ] Publish component and end-to-end results with project/category denominators. Fine-tuning, reranking and hybrid search require a measured failure hypothesis and their own plan.

## Plan review and handoff

The owner approved native execution with independent review and authorized G0 plus the first
one-project vertical increment on 2026-10-03. Checkboxes require verified evidence, not this
authorization alone. Corpus scale-up and
retrieval experiments are a separate gated follow-on, not an implicit release prerequisite.
