# Procurement interview demo corpus design

Date: 2026-10-03. Status: owner-approved; first increment in progress, no completed evaluation implied.

## Purpose

Make the Procurement Evidence Review Agent demonstrate selecting and assessing the right
evidence among plausible alternatives, while preserving the current small, explainable
walkthrough. The intended audience is the Scale AI Staff MLE, Public Sector interview track.
Success is a reliable live investigation with original-source evidence, explicit uncertainty,
review/restart recovery, and an honest evaluation report. Dataset size alone is not success.

This extends the direction in GitHub #12/#53/#66–#74. It proposes a bounded expansion of
#27/#29/#71 and a subsequent #62 benchmark; it does not silently change their current acceptance.
The two-focused-day budget in #12 covers the original agent slice. The expanded corpus path is
additional engineering work, not something already included in that estimate.

## Verified baseline

At main `b0cc77ef66e913161d143cf25691655064d5b5f8`:

- The packaged base BOM has two data rows; five companion XLSX workbooks have one each.
- The anomaly manifest has 29 assessment cases, four lifecycle cases, and 17 source entries.
- `application/showcase.py` pins the original comparison to GPU-A and one admitted order row.
- `application/chat.py` uses deterministic question routing; model orchestration is planned.
- #60 is closed and its correction merged. The handoff and milestone map contain stale text.
- Public `/` and `/healthz` returned HTTP 404 on 2026-10-03; the cause is not established.

These observations establish engineering scope, not current scientific or deployment acceptance.

## Corpus tiers and delivery gates

### A: preserved golden examples

Keep the existing artifacts, hashes, legacy scenario IDs, and expected response semantics intact.
They remain explanation aids and regression oracles. Do not regenerate them as part of expansion.

### B1: richer end-to-end pilot

Create four project bundles, six XLSX documents per project, and forty data rows per document:
24 documents and 960 source-row occurrences. The same entities can recur across documents;
report unique entities, documents, projects, and source rows separately.

Each project contains two BOM revision documents, two synthetic order-observation snapshots,
and two non-governing distractor workbooks. All use the existing admitted XLSX column schema.
The first release varies row order, descriptions, quantities, identifiers, revision relationships,
and applicability, not parser layout or file format. It does not claim extraction robustness.
Structured JSON sidecars explicitly declare synthetic document authority, scope, timestamps,
identity, approval, supersession and coverage facts with stable record locations. They are
inspectable fixture evidence, not facts inferred from filenames or model output.

Each project contains distinct target items for mismatch, match, conflicting requirement, and
missing observation. Include similar identifiers and irrelevant rows. Author exact replay,
independent line identity, future and superseded evidence as additional targeted cases.
Missing observations have insufficient coverage and yield not-assessed; they do not establish
missing PO. No receipt, outstanding quantity, forecasting, remediation, or general PO ingestion.

Use 48 independently labeled queries: twelve per project. Two projects are development
(24 queries), one validation (12), and one test (12). Each project has three exact-identifier,
three paraphrase, two temporal/revision, two missing/conflicting-evidence, and two
unsupported/ambiguous-request cases. Keep every revision and dependent artifact in its project
split. Validation/test use different entity vocabularies, authored query phrasings, and
scenario combinations. Record shared document schema/generator ancestry explicitly.

Test labels are withheld from the application and model context. A public repository cannot
provide a secret benchmark; call this a development-held-out synthetic test, not a blind or
contamination-proof evaluation. Once inspected for tuning, retire that test version and create
a fresh one. This is separate from the protected development-agent evaluator in #116.

### B2: benchmark expansion, after B1 works through the real caller

Target 20 projects, 120 documents, 4,800 source-row occurrences, and 200 labeled queries.
Split projects 12 development / 4 validation / 4 test, with ten queries per project.
Counts are workload targets, not evidence of statistical sufficiency. Add separately authored
scenario families and counterexamples before adding more repetitions. Any new workbook schema,
unit conversion, entity-resolution policy, or source format needs its own adapter/semantic slice
and benchmarks under #30/#31/#32/#43/#45 as applicable.

### C: optional load corpus

Larger generated replicas measure startup, indexing, memory and query latency only. Report
them separately. Repetition does not add independent semantic quality evidence.

## Contract and architecture

Authoritative inputs are admitted XLSX bytes and versioned synthetic source-metadata records.
Parse values from actual artifacts; never supply answer values from gold labels or case names.
The output contains qualified assessment status/reason, authoritative values where established,
governing decision, policy identity, input snapshot identity and resolvable evidence references.

Use server-owned RequestContext, explicit canonical item key and timezone-aware as-of time.
Reject unauthorized project selection before any search or source access. The demo serves a
fixed synthetic tenant; an allowlist of synthetic projects is a demonstration boundary, not
production tenancy. Ambiguous model interpretation requires clarification, not guessed identity.

Reuse governing-claim policy v1, ADR-019/023/024/026, the qualified assessment contract, and
AnomalyService. No new business policy is implied by a larger dataset. Search returns candidates;
the assessment service resolves the complete admitted scoped item/revision inventory before
evaluating. A truncated top-k list or empty search result cannot establish coverage or absence.
Do not sum BOM revisions as independent requirements.

Separate artifact generation, runtime admission, deterministic investigation and evaluation.
Domain values use stdlib dataclasses and Decimal; external mechanics remain behind a Protocol.
Retain the legacy scenario path and introduce a separate corpus investigation HTTP path with
project/item/as-of controls. Reuse the existing source viewer using hash-verified artifact lookup.
The agent and HTTP caller share the same investigation service.

Invalid schema, path traversal, hash mismatch and unsupported versions fail explicitly before
admission. Scope failure is forbidden; unknown artifacts/items are not-found; unsupported or
malformed requests are validation failures. Missing/conflicting business evidence is a successful
typed assessment with not-assessed disposition, not an exception or zero. Add any new error codes
through the repository's typed-error contract, without reinterpreting existing routes.

An implementation ADR must record corpus admission, scope binding, search-versus-assessment,
and runtime/evaluator separation before architecture changes. Runtime packages must not include
gold answers, qrels, split-purpose labels, or oracle-only case descriptions.

## Gold evidence and evaluation

Write scenario specifications and explicit gold outcomes before running the implementation.
The generator may render documents and stable IDs, but it must not call production governance,
reconciliation, or anomaly functions to produce expected labels. Independently audit every pilot
gold query against source rows and sidecar authority facts. Record reviewer identity, corrections,
and provenance. Metamorphic checks supplement this audit; they do not replace it.

Exact quantities use Decimal with zero tolerance where governing policy specifies it. Gold
records identify required and optional evidence roles, eligible alternative supporting sets,
expected disposition and reason, and expected clarification or rejection. A citation resolving
to an artifact is not sufficient proof that it supports the claim.

Report per-query results and category denominators, evidence-set completeness, authoritative
value/status agreement, false confident answers, appropriate abstention and source-location
resolution. For retrieval, report Recall@5/@10 and nDCG@10 only for queries with suitable qrels;
report unsupported queries separately. Report latency distributions with sample counts and
warm/cold conditions, tool/model calls, tokens and cost when observed; unavailable cost stays null.
Keep correlated queries grouped by project and avoid broad accuracy claims from twelve test cases.

Release requires all pilot deterministic gold cases to pass, all required source links to resolve,
and zero observed unauthorized reads, fabricated success, stale approval acceptance or duplicate
saves in the acceptance suite. Run each of the three live agent walkthrough scenarios three times;
report all nine runs. Additional paraphrase tests are evaluation evidence, not a promise of general
language coverage. Any unsupported numeric/status assertion or safety-boundary failure blocks
release; model/tool errors must be surfaced and count as failed runs, not silently excluded.

## Live demo and scope control

The [LangChain Academy study](../../langchain-ref/README.md) refines execution requirements:
define application-owned run/event contracts and evaluator expectations before graph construction.
Use fresh isolated threads for independent examples and one serial bounded workflow initially.
Scope checks precede checkpoint access. Public streams use explicit allowlisted fields; private
graph channels or output schemas are not a redaction mechanism.

Review resumes through an authenticated, persisted receipt bound to the exact brief and evidence
snapshot. The save service revalidates it. Recovery acceptance includes a crash after durable save
but before graph checkpoint completion, followed by replay with one saved result. Changed content
or evidence, expired approvals and checkpoint forks cannot reuse stale authority.

Trajectory evaluations distinguish pass, fail, unknown and not-applicable. Missing required audit
events block acceptance; duplicate telemetry events must be distinguished from duplicate durable
saves. Record actual timestamps and exclude fixture/replay runs from live measurements. LangSmith
export remains optional and cannot own application audit, approval or recovery state.

Show natural-language request -> scoped evidence selection -> deterministic assessment -> brief
with original cells -> exact-brief approval -> process restart/resume -> one saved result.
Show mismatch, unresolved requirement and missing observation. Keep execution traces separate
from domain provenance. A valid model request is interpreted, not selected by an answer-bearing
scenario ID. The deterministic baseline remains available and is labeled accordingly.

Restore and verify current hosting first. Integrate the pilot service into #66/#53, then execute
#67/#68 recovery and #72/#73/#74 release acceptance. Do not add another orchestration subsystem.
Do not start B2, embeddings, training, public datasets, arbitrary uploads, graph infrastructure,
geospatial features, or another product integration until the end-to-end pilot passes.
Local offline deterministic operation is not proof of disconnected model inference.

## Governing record

Read #12, #27, #29, #32, #36, #48, #53, #55, #57, #60, #62 and #66–#74 before execution;
read additional policy issues whenever their surface is touched. Planning reconciliation should
record this corpus expansion under #27/#29/#62 and explicitly amend the three-fixture limit in
#71 before implementation. Preserve broader acceptance and do not close umbrella issues early.

Implementation sequence: [delivery plan](../plans/2026-10-03-procurement-demo-corpus.md).
