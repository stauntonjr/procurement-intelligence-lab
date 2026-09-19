# Procurement Showcase Maturity Plan

> **For agentic workers:** Use `superpowers:executing-plans` to execute approved slices with review checkpoints. Checkboxes track deliverables, not authorization to invent policy or close umbrella issues.

**Goal:** Make the independent procurement demo demonstrate an auditable decision under conflicting evidence, with an employer-readable explanation and source inspection.

**Architecture:** Preserve deterministic procurement services and evidence identities. Add a versioned synthetic discrepancy scenario, expose service-owned decision/calculation evidence, and present it through the existing browser adapter. Retrieval, model integration, and SciFact remain independent.

**Tech stack:** Existing Python 3.12–3.13 package, stdlib dataclasses and HTTP adapter, Decimal arithmetic, XLSX fixtures, HTML/CSS/JavaScript, pytest and the existing semantic-quality harness.

**Specification:** [Procurement use cases](../../product/use-cases.md), [current demo acceptance](../../project/inspector-demo-acceptance.md), [parallel product direction](../../project/parallel-product-development.md), and the governing issues linked below.

**Status:** Planned on 2026-09-18. The owner requested this plan; this file does not claim that the richer scenario or policy is implemented. Start from the accepted local showcase implementation `ee90446`; inspect current code and live issue state before execution.

## Baseline and completion boundary

The current demo has two synthetic BOM rows, three keyword-routed questions, readable values,
claim status, clickable trace/evidence links, and parsed XLSX source-row inspection. Its README
GIF contains three captured browser states. It does not yet explain an explicit temporal revision
decision, expose a calculation breakdown, or render the original spreadsheet cells.

The next showcase is complete when a reviewer can answer, within a short walkthrough:

1. What disagreeing sources were supplied?
2. Which quantity is applicable to this project/site and as-of time, and why?
3. What evidence and versioned policy produced that decision?
4. Which conflicting or superseded assertions were retained?
5. What does the system decline to establish when authority is ambiguous?

Keep the current working demo available throughout. Deliver each slice independently; the first
showcase improvement need not wait for full M4/M5 acceptance.

## Authority and scope

| Work | Governing issues | Boundary |
|---|---|---|
| Required-quantity discrepancy and governing decision | [#15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15), [#46](https://github.com/stauntonjr/procurement-intelligence-lab/issues/46) | A required-quantity policy slice; not every procurement predicate |
| Revision, approval and as-of eligibility | [#38](https://github.com/stauntonjr/procurement-intelligence-lab/issues/38) | Distinguish effective, observed, document and ingestion times |
| Claim explanation and inspector | [#49](https://github.com/stauntonjr/procurement-intelligence-lab/issues/49), [#50](https://github.com/stauntonjr/procurement-intelligence-lab/issues/50) | Machine-readable evidence first, UI second |
| Source highlighting | [#58](https://github.com/stauntonjr/procurement-intelligence-lab/issues/58) | XLSX cell-grid subset first; PDF remains separate |
| Optional scenario cost extension | [#52](https://github.com/stauntonjr/procurement-intelligence-lab/issues/52) | Explicit price/currency/effectivity evidence; no invented price or currency |

Use `Part of` for these issues until their complete acceptance criteria are met. Before each
implementation slice, create or reuse a bounded work item with its exact contract. Review the
roadmap stewardship audit and Project state at the start of the semantic slice. This plan records
sequence; it does not change GitHub planning state.

No LLM, vector store, shared-platform migration, production deployment, purchasing action,
forecasting, receipt workflow, or full spreadsheet editor is required. Treat unknown and
unresolved as distinct from zero. Do not add confidential data.

## Slice 1 — Freeze a discrepancy scenario and decision contract

**Files to read:** `docs/product/use-cases.md`, `docs/adr/015-append-only-assertion-ledger.md`,
`docs/adr/019-explicit-request-scope.md`, `docs/adr/020-expected-observed-state.md`,
`src/procurement_intelligence_lab/domains/procurement/reconciliation.py`,
`src/procurement_intelligence_lab/platform/semantics/reconciliation.py`, and
`src/procurement_intelligence_lab/application/pipeline.py`.

**Proposed deliverables:** `docs/product/showcase-discrepancy-contract.md`,
`src/procurement_intelligence_lab/examples/showcase/` synthetic XLSX inputs and versioned manifest,
and `tests/contract/test_showcase_discrepancy.py` with literal expected values and evidence locations.

- [ ] Start with one canonical GPU SKU, one project/site, and two BOM revisions. Proposed story:
  revision A states 4 GPUs, revision B states 6. Include an explicit approval/effectivity record;
  a larger revision number or later ingestion time must not establish authority by itself.
- [ ] Record policy ID/version, required-quantity precedence, approval evidence, effective interval,
  query as-of time, tie behavior, and unresolved behavior in the governing issue/contract before
  implementing selection. Ratify any architectural change through an ADR.
- [ ] Define the relationship between disagreement and answer eligibility explicitly. Today
  `reconcile_lines` can select a governing source while retaining `conflict`, and the claim
  service can withhold the value. Do not silently relabel this result as reconciled to make the
  demonstration look successful. Specify whether the public response carries an applicable
  value plus a conflict diagnostic or abstains, and how each is distinguished.
- [ ] Freeze gold source hashes, sheet names, cell addresses, assertion IDs, expected decision
  outcomes, and a literal hand-checked explanation. Keep reference outcomes separate from
  application input; runtime must not read the gold answers.
- [ ] Include cases before B becomes effective, after it becomes effective with valid authority,
  missing approval, and equally authoritative incompatible assertions. The approval/tie rules
  must come from the ratified contract, not this illustrative story.

**Exit:** A reviewer can determine the expected result and retained evidence for every case
without executing the application. No semantic implementation proceeds with unresolved policy.

## Slice 2 — Deliver the deterministic discrepancy result

**Modify as warranted:** `domains/procurement/assertions.py`, `domains/procurement/reconciliation.py`,
`domains/procurement/state.py`, `application/pipeline.py`, and `application/evidence_service.py`
under `src/procurement_intelligence_lab/`. Reuse platform contracts; do not specialize them by
importing the procurement vertical. Extend `tests/unit/test_reconciliation.py`,
`tests/contract/test_claim_semantics.py`, and the new discrepancy contract tests.

**Interface contract:** Input is scoped canonicalized assertions, explicit approval/revision/time
metadata and a versioned policy. Output retains governing and non-governing assertion IDs,
eligibility reasons, policy identity, decision status, applicable value or explicit abstention,
and EvidenceRefs. Final Python types/signatures belong in Slice 1's reviewed contract.

- [ ] Write failing tests for the frozen cases through the application service before changing
  domain rules. Assert identity and evidence lineage as well as the number.
- [ ] Implement the smallest required-quantity policy path. Preserve every losing, stale,
  conflicting and unresolved assertion; do not merge revisions by summing them.
- [ ] Test input-order independence, duplicate handling, cross-scope rejection, future/stale
  records, effectivity boundaries and ties. Apply the existing numeric policy to zero, negative
  and fractional inputs; do not introduce a new validation rule only in the UI.
- [ ] Expose the decision as typed application data. Keep authoritative arithmetic and eligibility
  outside JavaScript and generated prose.
- [ ] Run focused semantic tests and the repository gate; record current-revision evidence and
  review. Add a regression oracle/challenge if a shipped semantic defect is discovered.

**Exit:** The application returns the contract's explicit result for both a governed case and an
abstention case, with retained alternatives. This does not complete all of Issue #15.

## Slice 3 — Explain the decision in the browser

**Modify:** `application/evidence_service.py`, `interfaces/web.py`,
`tests/unit/test_web.py`, `tests/integration/test_web_happy_path.py`, and
`docs/project/inspector-demo-acceptance.md`. Add focused browser acceptance coverage for the new
branching behavior. Preserve existing endpoint clients or version incompatible contracts.

- [ ] Add an explicit scenario/question selector and scope/as-of summary. Label the current
  interaction as supported queries; do not imply unrestricted conversational understanding.
- [ ] Render the service's decision: applicable quantity or abstention, selected source, policy
  version, approval/effectivity reason, and retained alternatives with their dispositions.
- [ ] Show the authoritative operands and operation when aggregation is actually involved. Do not
  invent a “4 + 2” calculation for a revision that simply replaces a requirement of 4 with 6.
- [ ] Make each decision operand/source reference clickable. Display unavailable provenance
  explicitly and preserve source/query race protection, error recovery and keyboard navigation.
- [ ] Verify the normal case, competing-authority case and missing-approval case through the
  shipped browser and actual HTTP requests. Include switching scenarios while requests are
  pending so evidence cannot remain attached to the wrong answer.

**Exit:** A viewer can explain why a claim governs, or why no result is established, using only
what is visible in the application. The frontend never selects the winner.

## Slice 4 — Show the original XLSX cells

**Modify:** `adapters/xlsx.py`, `interfaces/web.py` and source evidence serialization as needed.
**Tests:** `tests/contract/test_xlsx_coordinates.py`, `tests/unit/test_xlsx_adapter.py`, and
`tests/integration/test_web_happy_path.py`.

- [ ] Expose a bounded read-only grid from the admitted original synthetic workbook, preserving
  actual sheet/row/column coordinates and source content hash. Retain raw source text separately
  from normalized quantities and prices; never reconstruct “original” cells from domain values.
- [ ] Highlight only the cells referenced by the selected EvidenceRef. Show original and
  normalized values side by side when they differ.
- [ ] Keep source lookup keyed by admitted evidence identity. Do not accept arbitrary filesystem
  paths from the browser. Preserve existing request-scope checks.
- [ ] Test sparse cells, blank cells, multiple referenced cells, wrong hash, unavailable source,
  unknown identifier and denied scope. Confirm the browser display against the actual workbook.
- [ ] Recheck the clean wheel includes all required fixtures/resources. Label this as an XLSX
  subset, with no PDF or full-workbook editing claim.

**Exit:** The viewer can visually match a claim to original synthetic cell content and coordinates.
This can proceed alongside Slice 2 using the current fixture and agreed source contract.

## Slice 5 — Publish a clearer showcase packet

**Modify:** `README.md`, `docs/assets/procurement-demo.gif`,
`docs/assets/procurement-demo.png`, and `docs/project/inspector-demo-acceptance.md`.

- [ ] Capture actual browser interactions: choose discrepancy scenario, inspect the decision,
  open its source, and reveal the retained competing assertion. Record commit, fixture and policy
  identities with the capture. Use a stable accepted revision, not an in-progress branch.
- [ ] Create a short approximately 20–30-second GIF with visible interactions and readable pauses.
  Target under 5 MB; preserve legibility before optimizing size. Disclose edited timing and do
  not present it as a latency measurement. Retain a static image for accessibility.
- [ ] Link a longer walkthrough only when it exists. It should include the abstention case and
  distinguish implemented capabilities from planned procurement workflows.
- [ ] Verify the README rendering and media links, and update handoff/milestone wording without
  claiming completion of the broader M4/M5 milestones.

**Exit:** Someone unfamiliar with the repository can see the problem, decision, evidence and
limitation without installing the project. Public app hosting remains a separate decision.

## Sequence, validation and stop conditions

- Priority path: Slice 1 → Slice 2 → Slice 3 → final capture in Slice 5.
- Slice 4 may run independently after the evidence identity/source contract is frozen. The
  supported-query wording from Slice 3 can ship earlier without the new semantic behavior.
- Keep scenario cost extensions optional and separate under #52; the quantity discrepancy alone
  is sufficient to make this showcase more meaningful.
- For each semantic slice, use `.agents/skills/semantic-change-loop/SKILL.md`; write failing
  contract tests, run focused tests, test the real public caller, and review the latest revision.
- Final gate: `make check`, `make integration`, `make package-smoke`, `make challenges`,
  `git diff --check`, and validated `docs/development/semantic-change-evidence.schema.json`
  evidence. Separate successful engineering checks from product and model-quality claims.
- Stop the dependent implementation when policy authority is ambiguous, a source cannot be
  traced, scope/time evidence is missing, or a required check fails. Keep unaffected presentation
  work moving. Do not weaken the contract to obtain a more attractive demonstration.
