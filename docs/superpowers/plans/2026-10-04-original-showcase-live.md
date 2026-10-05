# Original showcase live review implementation plan

> For agentic workers: use superpowers:executing-plans inline; one independent whole-branch review.

Goal: execute the original three January showcase snapshots through existing live intent, exact review and source controls.
Architecture: reuse showcase_order_comparison as numerical/policy authority; inject read-only source/catalog mechanics at composition. No second workflow, data expansion or prompt tuning.
Tech stack: existing Python/stdlib, optional pinned LangGraph and development Playwright.
Spec: ../specs/2026-10-03-procurement-demo-corpus-design.md, especially original scenario preservation; #66/#71/#72.
Primary #71/M9, part of #53/#66/#67/#68/#70/#72/#74. Stacked on PR184; no merge/deployment.

## Global constraints

Preserve legacy routes/IDs/bytes and all corpus behavior. Use only existing original XLSX files.
Source configuration is server-owned before inference; physical names are corpus,
showcase-a-order, showcase-a-b-order, showcase-a-only. Never submit source-set/scenario names,
quantities, gold or status to the model. Original scope synthetic-tenant/synthetic-project/synthetic-site;
item GPU-A, fixed cutoff2026-01-15T00:00:00Z. Other dates/items fail before business assessment;
source integrity/scope checks precede source access. Original observed order2 survives unresolved
requirement, but remains an unassessed observation. Show that distinction in the original page.
Default corpus scope/date/assessed quantity semantics are unchanged. No model reload/providers,
uploads, training, corpus expansion or production authentication. Live model is selected local Qwen;
one attempt per authored question, nine original walkthrough submissions total.

## Task 1: source/catalog port and original deterministic bridge

Interfaces: ReviewSources.items/snapshot_id/source_ids/source_by_id(context); Investigator.investigate(request,context).

- [ ] Add failing contracts for three original snapshots: complete governed/assessment IDs and
  values match direct original service, original EvidenceRefs/cells resolve, conflict observation2
  remains not_assessed, missing observationnull, fixed cutoff/item rejection, unauthorized scope,
  unsupported source set, tampered/missing/malformed manifest/workbook and changed source bytes.
- [ ] Run tests; expected missing source/bridge module failure.
- [ ] Record ADR033: source-set injection and minimal catalog port; pin hashes of existing
  three original files in one resource manifest (no answers/labels). Implement source mechanics
  behind ReviewSources and original service wrapper preserving policy/claim IDs; no copied math.
  Add default corpus items/snapshot methods and Investigator Protocol without changing results.
- [ ] Run new source/bridge contracts plus existing corpus/question/tool contracts; expected green.
  Commit.

## Task 2: real public composition and source-aware controls

Interfaces: Task1 sources/Investigator consumed by source factory, workflow/live CLI and ReviewServer.

- [ ] Write failing actual HTTP/CLI tests selecting sources with --sources (default corpus),
  synthetic-project/site and January cutoff. Controlled model proposal stays independent of source
  selection and cannot override it. Test exact save/repeated save, rejection, restart/recovery,
  incompatible cross-source recovery before tools, wrong project and request-supplied source field.
  Test source membership and original observed-versus-assessed labels through actual page markup.
- [ ] Run tests; expected missing selection/composition failure.
- [ ] Centralize composition source selection and scope metadata; compose_services/compose_live/
  compose_question accept sources keyword; existing callers retain defaults. Expose configured
  fixture/live CLI and browser options only, no arbitrary upload/path. Page shows configured source
  context and literal GPU-A, original fixed cutoff and observed-order label; corpus page unchanged.
- [ ] Rebuild/install clean wheel; run focused tests, public installed fixture workflows and
  package-smoke original resource/commands. Expected green. Commit.

## Task 3: nine installed live original browser trials and closeout

Interfaces: Task2 clean installed wheel; frozen manifest independent of runtime, redacted immutable results.

- [ ] Freeze caller/manifest/model/source/prompt/tool/app/wheel versions before calls. Three
  repetitions for each source-set through actual browser with selected local Qwen; match direct
  original baseline complete fact/policy IDs, all original source cells, review/repeated save,
  rejection and owned restart/recovery with no recalled inference. Record all nine attempts and
  journals/events/saves; failures/unknowns retained, no retries/tuning. Disposable credentials removed.
- [ ] Run make check, package-smoke, current/known-bad challenges, existing corpus browser fixture
  checks and installed original live acceptance. Expected all required checks pass; retain failures.
- [ ] Update handoff/README/milestone map/contract/results, distinguishing original observed order
  from assessment and original source acceptance from held-out quality/deployment/fullG2.
- [ ] One independent whole-branch reviewer; Important/Critical get one RED/GREEN author pass,
  minors deferred. Exact-head semantic evidence/PR contract; push stacked draft and verify CI;
  inspect/update/re-read #71/#72 and audit Project without broader Issue closure. Expected verified draft.

## Review Focus

Original claim/policy/evidence/byte preservation; original observed order2 versus unassessed status;
source configuration never model-selected; scope/site/cutoff and source versions bind recovery;
missing/corrupted files fail before confident results; source membership and admission before reads;
catalog read versus audited business tools; clean wheel resources and real installed/browser caller;
source context and quantity labels; credential lifetime and redaction; immutable attempt denominators,
no prompt tuning or new data and no held-out/deployment/fullG2 completion claim.
