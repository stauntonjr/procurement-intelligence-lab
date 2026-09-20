# Issue #60: Expected-versus-observed anomaly implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Use `superpowers:subagent-driven-development` only if that execution approach is selected. Checkboxes track implementation, not work completed by writing this plan.

**Goal:** Complete the deterministic anomaly acceptance of [Issue #60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60), building on the shipped quantity showcase, with qualified comparisons, evidence-backed abstentions, reproducible policies, and auditable lifecycle transitions.

**Architecture:** Procurement owns input qualification, per-kind comparison policies, and orchestration. The platform retains the generic immutable anomaly envelope. Application services supply authorized scope and explicit policy/configuration through the composition root; adapters load source material and retain append-only records without deciding procurement meaning.

**Tech stack:** Existing Python/uv project, stdlib dataclasses and Protocols, Decimal, pytest, existing HTTP inspector, existing stable-ID and provenance utilities. No new framework, model, database, or external integration is required.

**Spec:** Issue #60; `docs/adr/016-expected-observed-anomalies.md`, ADR-020, ADR-023, ADR-024; `docs/product/governing-claim-policy-v1.md`; and `docs/product/showcase-order-comparison.md` on current main. Task 1 records the proposed contract extensions before runtime changes.

## Baseline and scope

Prepared 2026-09-19 against fetched `origin/main` **27cda4500e9aecd9707c5ce6c0c3a38f202344be**. The working checkout is an older planning branch at `7b81f26`; implementation must start from freshly verified main, not this checkout's runtime files. This document is a proposal, not an accepted ADR or implementation claim.

Verified live: #15 and #47 are closed. #60 is open in M7; its Project #6 status is `Todo`. PR #168 delivered the bounded order comparison at `cff0905398909fe9378dfd4f3ce4ce2f9da6895c`. The current handoff correctly records that boundary. The planning audit found no missing configured fields, labels, milestones, or views (106 issues, 107 Project items, 25 fields). The latest roadmap-stewardship run, [35462343578](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/35462343578), failed with Gemini quota exhaustion; it is not successful audit evidence. A fresh successful advisory run remains part of execution orientation; the issue/code/Project inspection here supports this plan independently.

Already present; preserve and extend:

- `platform/semantics/anomalies.py`: generic `Anomaly`, stable identity, severity, and `OPEN`, `SUPPRESSED`, `IN_REVIEW`, `RESOLVED` enum values. Enum values do not implement an audited transition workflow.
- `domains/procurement/anomalies.py`: eight kinds, typed details, independent policy dataclasses, four standalone detectors, and partial state orchestration. Do not rebuild this taxonomy.
- `domains/procurement/state.py`: scoped expected/observed projections, finite/non-negative quantities, evidence, and as-of pairing. #118 remains open and governs broader invariant acceptance.
- `application/showcase.py::showcase_order_comparison`: admitted synthetic XLSX order row plus governed requirement. Four scenarios are mismatch, matched, missing observation, and unresolved requirement. Missing/unresolved returns `not_assessed`.
- `interfaces/web.py::_showcase_claim_payload`, `tests/contract/test_showcase_discrepancy.py`, `tests/integration/test_web_happy_path.py`, and `tools/order_package_probe.py`: shipped response and evidence drill-down.

Important gap: `detect_expected_observed_anomalies` currently emits `missing_po` for `observed=None`, and tests encode that result. The raw revision helper equates any unequal revision labels with staleness. Neither establishes coverage or an explicit revision ordering. Treat corrections to these shipped semantics as regression work with challenge evidence.

## Global constraints

- “Core owns semantics; adapters own mechanics.” “Models produce evidence; policies produce decisions.”
- Use stdlib dataclasses for domain objects, Pydantic only at boundaries, explicit DI, and existing dependency checks. Platform/ports must not import procurement.
- Inputs are governed state/claims and explicit policies; output is anomalies or explicit per-kind assessment dispositions. Preserve source assertions, rejected candidates, state identity, and claim-level evidence.
- Scope includes tenant/project/site and governed projection version; every query has a timezone-aware as-of. Revision labels are source metadata, not projection identity or sortable authority.
- Unknown, absent, conflicting, stale, and partial are never silently converted into zero or a successful match.
- Anomaly detection performs no forecast, recommendation, approval, procurement write, identity merge, or source correction.
- No general ERP/PO ingestion, receipt accounting, FX conversion, automatic substitution approval, production review UI, or database rollout in this issue. A typed, admitted synthetic input path is sufficient to demonstrate detectors, but must exercise real source loading and the public caller.
- Preserve the existing public showcase and its error mapping (403 scope, 422 invalid request, 404 missing source). Adding taxonomy examples must not grant writes to the public deployment.
- Use the repository semantic-change loop, latest-revision evidence schema, real-caller validation, clean-package smoke when resources change, and a regression oracle/challenge for each shipped semantic defect.

## Review focus

1. Missing versus complete-empty order coverage: only the latter can support a missing-PO finding (Tasks 1–3).
2. Duplicate line identities, incompatible units/currencies, and conflicting effective records: abstain without double counting (Tasks 2–3).
3. As-of boundaries and source revisions: future/other-scope records never pair; unequal labels alone do not establish staleness (Tasks 2–3).
4. Changed policy parameters under the same human-readable policy ID: retained canonical configuration must change provenance/assessment identity (Tasks 2–3).
5. Suppression, replay, and recomputation: a lifecycle event must reference one exact anomaly and cannot erase it or transfer silently to a new assessment (Tasks 4–5).

## Chosen delivery sequence

Use three reviewable slices: **A: qualified quantity/coverage assessment** (Tasks 1–2), **B: remaining taxonomy and auditable policies** (Task 3), **C: lifecycle plus public acceptance** (Tasks 4–6). Every intermediate PR says `Part of #60`. Only the final acceptance audit may use `Closes #60`.

This is preferable to expanding the showcase function into a general detector or introducing a generic runtime/plugin registry: the first mixes source admission with policy, and the second adds infrastructure unnecessary for this issue. Extend the existing domain helpers behind one explicit application service.

## Proposed assessment contract

Record these decisions in Task 1's product contract and ADR; they are proposed extensions to the accepted baseline.

| Concern | Contract |
|---|---|
| Assessment result | One result per requested kind: `anomaly`, `clear`, `not_assessed`, or `not_applicable`; optional anomaly, typed reason, evidence, policy/config digest, input IDs, scope, as-of. An empty anomaly list alone is not success. |
| Evidence | Retain requirement, observation, governance decision, coverage/revision/review evidence by role. The existing envelope still contains a unique flat EvidenceRef set for compatibility. |
| Missing PO | Required quantity exceeds the configured minimum and current, complete, authoritative coverage for the exact item/scope/as-of establishes no applicable approved PO line. Absence of data is `not_assessed/missing_observation`. A zero-quantity PO is not automatically an absent PO. |
| Quantity | Compare governed required quantity with sum of independently identified eligible PO lines in the same unit. Exact duplicate assertion replays do not add quantity; ambiguous duplicate relationships or competing versions abstain. Absolute difference strictly greater than tolerance emits mismatch; equality to tolerance clears. |
| Coverage | Incomplete/stale observation may produce `coverage_gap` only from explicit coverage/freshness evidence. It must not justify a quantity match or a missing-PO finding. Unknown observation quantity remains separate from numeric order totals. |
| Substitution | Positive evidenced substituted quantity above its tolerance is a substitution finding. A substitute relationship is not same-as identity or approval. |
| Revision | Emit stale revision only for an applicable observed source revision explicitly superseded at as-of by the governed requirement revision. Unrelated/ambiguous labels abstain; same revision clears. Keep the supersession path as evidence. |
| Price | Compare governed planned and committed unit prices only with identical currency, unit, and price basis. Conflicts/missing basis abstain. Use Decimal and absolute currency-unit tolerance; no FX or implicit quote fallback. |
| Schedule | Compare an evidenced required-by date with a supplier-confirmed PO commitment. Commitment later than required-by plus tolerance emits `late_commitment`. Missing required-by/confirmation abstains. This is a deterministic commitment comparison, not a prediction of delivery. |
| Identity | Emit unresolved identity from an explicit unresolved/ambiguous resolution decision and its mention evidence. Do not fabricate a canonical key or compare quantities/prices across unresolved identities. |
| Configuration | Immutable, validated per-kind policies; canonical serialization plus digest retained in decision provenance. Same ID with different configuration cannot alias to the same assessment. Defaults: existing zero numeric tolerance, zero schedule tolerance, warning findings, informational coverage; these are synthetic defaults, not real-world procurement recommendations. |
| Failures | Structurally invalid input uses existing `SemanticContractError`, `ScopeContractError`, or `TemporalContractError`; legitimate missing/conflicting business evidence returns a typed assessment disposition. Unexpected exceptions propagate to the existing server boundary. |

## Task 1: Freeze the contract, corpus, and architectural delta

**Files:** Create `docs/product/anomaly-assessment-v1.md`, `docs/adr/026-qualified-anomaly-assessment-and-lifecycle.md` (choose the next free ADR number if taken), and `evals/anomalies/v1/manifest.json`. Update ADR-016 to reference the superseding qualification/lifecycle decisions without rewriting its historical delivery claim.

**Consumes:** Above authoritative Issue/ADR contracts; existing four showcase scenarios.
**Produces:** Ratified input qualification, per-kind matrix, lifecycle transition table, and a versioned synthetic fixture manifest used by subsequent tasks.

- [ ] Refresh main and reread repository instructions, #60, #15/#47/#118, and later governing issues #41/#44/#52/#61/#65. Run/read the roadmap audit and deliberately review Project #6. Use an isolated execution branch according to the worktree skill.
- [ ] Document the proposed contract above, including the explicit coverage attestation and required-by source authority. For this issue only, admit these through a checked-in synthetic manifest with stable source IDs, hashes, scope, as-of, approval, and evidence; never infer completeness from an empty worksheet.
- [ ] Define fixture rows: each taxonomy kind positive/clear/unassessed, unresolved requirement, complete-empty coverage, incomplete-empty coverage, approved zero PO, two independent PO lines, exact replay, conflicting duplicate, stale/future/other-scope input, equal/unequal/superseded revisions, mismatched currencies/units, and lifecycle events. Every expected result includes exact kind/reason and evidence IDs. Freeze fixture hashes after generating the data in Task 2.
- [ ] Record the dependency boundary: #41 owns general reviews/corrections; #44 owns relationship semantics; #52 owns scenario costing; #61/#65 own forecasts/decisions. New source-authority rules or public writes require a separate scoped decision, not an invented implementation default.
- [ ] Review the ADR and contract before changing runtime semantics. Commit this contract with the slice A tests and implementation so the delivered behavior has one authoritative reference.

## Task 2: Qualified quantity and coverage through a shared assessment service

**Files:** Create `domains/procurement/anomaly_assessment.py` and `application/anomaly_service.py` under `src/procurement_intelligence_lab/`; create `tests/contract/test_anomaly_assessment.py`, `tests/regression/test_anomaly_qualification.py`; modify `domains/procurement/anomalies.py`, `application/showcase.py`, and `bootstrap.py`. Add admitted fixture resources under `src/procurement_intelligence_lab/examples/` and finalize `evals/anomalies/v1/manifest.json`.

**Interfaces:** Define immutable `AssessmentStatus`, `AssessmentReason`, `CoverageAttestation`, `AnomalyAssessmentInput`, and `AnomalyAssessment` in the procurement module. Input carries full scope/as-of, optional governed expected requirement, qualified ordered quantity/unit, ordered-line and decision IDs, evidence by role, and optional coverage attestation. Output carries per-kind status/reason, optional `Anomaly`, source/decision IDs, policy digest, scope/as-of. `assess_quantity(inputs, *, policy, provenance, detected_at) -> tuple[AnomalyAssessment, ...]` owns quantity, missing-PO, and coverage qualification. Application `AnomalyService.assess(inputs, *, request_context) -> tuple[AnomalyAssessment, ...]` authorizes scope and injects policy/time; it does not compute domain rules.

- [ ] Add failing contract cases before implementation. Preserve all four showcase outcomes. Add the following assertions using fixture inputs built from the manifest, not naked helper-only quantities:

```python
@pytest.mark.parametrize(
    "case, status, reason",
    [
        ("order_missing", "not_assessed", "missing_observation"),
        ("order_unresolved", "not_assessed", "unresolved_requirement"),
        ("complete_empty_orders", "anomaly", None),
        ("incomplete_empty_orders", "not_assessed", "incomplete_coverage"),
    ],
)
def test_missing_po_requires_positive_coverage_evidence(
    cases, service, context, case, status, reason
):
    results = service.assess(cases[case], request_context=context)
    result = next(r for r in results if r.kind.value == "missing_po")
    assert result.status.value == status
    assert (result.reason.value if result.reason else None) == reason
```

Here `cases`, `service`, and `context` are pytest fixtures created in `test_anomaly_assessment.py` from the manifest and the existing request-scope pattern. These are proposed test interfaces, not existing helpers.

- [ ] Run `uv run pytest -q tests/contract/test_anomaly_assessment.py` and record the expected red result for the missing implementation.
- [ ] Implement explicit coverage validation, source admission, approved-line aggregation under governing policy v1, exact replay handling, and abstention for ambiguous duplicates. Distinct PO lines sum; conflicting versions do not. Preserve per-line evidence and rejected input dispositions. Do not construct full `ObservedProcurement` with invented zero receipts to express an order-only input.
- [ ] Replace the unsafe legacy missing-observation branch and update its callers/tests to the qualified contract. Keep `detect_quantity_mismatch` as the arithmetic helper. Do not retain an unguarded public path that continues to infer missing PO from `None`.
- [ ] Route the existing showcase through the service while preserving response shape, statuses, source links, and admitted-fixture scope. Order-only scenarios may assess quantity but abstain on missing-PO inference without a coverage attestation.
- [ ] Add finite/non-negative, zero, fractional, overage, one/many, replay, conflicting duplicate, missing evidence, cross-scope, naive/future time, and exact tolerance tests. Test explicit as-of boundaries and reorder-invariant results; tie conflicts abstain instead of input-order selection. Keep unknown receipt/outstanding values unknown.
- [ ] Run the new suites, `tests/unit/test_anomalies.py`, `tests/regression/test_state_invariants.py`, and `tests/contract/test_showcase_discrepancy.py`. Add an executable development-agent challenge for the shipped absent-observation false positive using the next unused C-number and a known-bad mutation that restores it. Validate it through the existing challenge runner. Commit slice A with its evidence.

## Task 3: Complete the taxonomy and policy replay evidence

**Files:** Extend `domains/procurement/anomaly_assessment.py`, `domains/procurement/anomalies.py`, `application/anomaly_service.py`, fixture manifest/resources, and `tests/contract/test_anomaly_assessment.py`; create `tests/unit/test_anomaly_policy_identity.py`.

**Interfaces:** Extend `AnomalyAssessmentInput` with optional typed price pairs (Decimal value, currency, unit, basis, governing IDs), required-by/commitment dates, explicit revision supersession evidence, substitution quantity/relationship evidence, and resolution decision/mention evidence. Each comparison retains its own eligibility/status; an unavailable price does not block a qualified quantity result. Add `assess_anomalies(inputs, *, policies, provenance, detected_at) -> tuple[AnomalyAssessment, ...]`; the service delegates to it. Retain independent existing policy types, adding typed configuration fields only where required.

- [ ] Write parameterized failing tests for all eight kinds and their qualification gates. Require each manifest case to produce the exact expected kind/status/reason and evidence set, not merely a nonempty anomaly list.
- [ ] Qualify inputs before calling existing price/schedule/identity helpers. Change revision detection to require explicit supersession evidence rather than unequal strings; add its regression oracle and known-bad challenge. Positive substitution requires relationship evidence, never similarity. Keep the unsupported cases as explicit abstentions.
- [ ] Add cases for equal price, tolerance equality/just over, zero price, fractional money, missing/stale/conflicting quote, differing currencies and units; exact commitment tolerance, missing required-by, future approval, superseded confirmation; unrelated revision labels, equal jointly governing quantities across revisions; unresolved identity without an expected canonical key.
- [ ] Canonicalize each policy configuration using the existing stable serialization/ID conventions, sorting unordered input/evidence IDs and preserving Decimal/date semantics. Retain canonical config and digest in decision provenance; include snapshot IDs, implementation version, scope/as-of, and policy ID. Reject nonfinite/negative tolerances and blank IDs with typed errors.
- [ ] Add identity tests: replay/reordering/install location/detection wall-clock do not change semantic identity; changed threshold, scope, as-of, evidence, or governance decision changes assessment identity. Two configs with the same policy ID and different tolerance must not share provenance/anomaly identity. Preserve the existing Anomaly identity formula unless an ADR explicitly changes its compatibility contract.
- [ ] Run `uv run pytest -q tests/contract/test_anomaly_assessment.py tests/unit/test_anomaly_policy_identity.py tests/unit/test_anomalies.py` plus the two regression challenges. Commit slice B with updated semantic evidence.

## Task 4: Audited lifecycle without public mutation authority

**Files:** Create `src/procurement_intelligence_lab/platform/semantics/anomaly_lifecycle.py`, `tests/unit/test_anomaly_lifecycle.py`; integrate replay/read support in `application/anomaly_service.py`. Reuse existing generic review/provenance contracts where they fit; do not import procurement into the platform.

**Interfaces:** Immutable `AnomalyLifecycleEvent` contains event ID, anomaly ID, previous/new status, actor reference, timestamp, reason, evidence IDs, policy ID, and expected prior event ID. Pure `apply_lifecycle_event(anomaly, history, event) -> Anomaly` validates and returns a projection; it never modifies the original anomaly or source ledger. Application callers retain append-only events; reference acceptance loads a fixture event log. No persistent database or web write endpoint is added.

Proposed transitions: OPEN→IN_REVIEW/SUPPRESSED/RESOLVED; IN_REVIEW→OPEN/SUPPRESSED/RESOLVED; SUPPRESSED→OPEN/IN_REVIEW/RESOLVED; RESOLVED→OPEN only with explicit reopening evidence. Resolution requires adjudication/comparison evidence, not an empty detection result. Suppression always requires actor, reason, policy, and evidence. All transitions validate previous status/event identity; exact event replay is idempotent, divergent reuse fails.

- [ ] Write failing tests for every permitted transition and rejected self/illegal transition, wrong anomaly/scope, missing actor/reason/evidence, naive/future event time, stale prior-event ID, exact replay, and conflicting event-ID reuse.
- [ ] Implement the pure reducer and canonical event identity. Keep event IDs and status history distinct from the anomaly detection ID. Require chronological replay with explicit predecessor IDs; do not silently reorder conflicting history.
- [ ] Test that suppression and resolution retain the detection's source evidence and original OPEN record. Recomputing a changed assessment creates a distinct anomaly and does not inherit suppression. Reopening an unchanged resolved finding is an explicit event, never a detector side effect.
- [ ] Run `uv run pytest -q tests/unit/test_anomaly_lifecycle.py tests/contract/test_anomaly_assessment.py`. Commit the lifecycle portion with a reviewed transition contract. Production review orchestration/authorization remains #41/#56/#67 work.

## Task 5: Exercise the actual HTTP and installed-package path

**Files:** Modify `application/showcase.py`, `interfaces/web.py`, `tests/integration/test_web_happy_path.py`, `tests/contract/test_showcase_discrepancy.py`, `tools/order_package_probe.py`, `tools/package_smoke.py`, and packaged synthetic examples. Preserve existing deployment restrictions.

**Consumes:** `AnomalyService.assess` and lifecycle projections from Tasks 2–4.
**Produces:** Read-only inspector examples for all kinds, abstentions, policy/config details, and retained lifecycle history, with original-source links.

- [ ] Add failing real HTTP cases using the existing server/form harness for quantity mismatch, qualified missing PO, incomplete coverage, price mismatch, late commitment, explicit stale revision, substitution, unresolved identity, and read-only suppressed/reviewed/resolved examples. Load lifecycle states from explicit synthetic event fixtures; do not offer public write controls.
- [ ] Serialize per-kind assessment status separately from anomaly lifecycle status. Display expected/observed values with units/currencies, reason, scope/as-of, policy ID and digest, governance IDs, both source sides, coverage evidence, and lifecycle reasons. Mark `not_assessed` clearly; never render it as “matched.”
- [ ] Verify every returned source link through HTTP, including coverage, supersession, and lifecycle evidence. Verify 403/422/404 behavior and that caller-supplied scope/values cannot bypass fixture admission. Preserve all four original scenario results.
- [ ] Extend the clean-wheel probe to run representative taxonomy and lifecycle examples outside the checkout, with stable logical artifact IDs across separate install directories. Verify packaged fixture presence and source drill-down. Run `make package-smoke` and the real HTTP suite. Commit public acceptance into slice C.

## Task 6: Evidence, review, and issue close-out

**Files:** Update `docs/project/handoff.md`, `docs/development/milestone-map.md`, `docs/product/anomaly-assessment-v1.md`, and the showcase acceptance document. Add final semantic evidence under the repository's schema and update challenge manifests/routing only where touched.

- [ ] Record every applicable scenario family (empty, one, many, duplicate, conflict, missing, stale, future, cross-scope, zero, negative, fractional, boundary) with test references, or a concrete not-applicable rationale. Tie fixture manifest/hash, policy configs, command argv/results, and review to the exact revision.
- [ ] Run the required acceptance commands on the final implementation revision:

```bash
make check
make package-smoke
make challenges
uv run python tools/validate_semantic_change.py --evidence artifacts/issue-60-semantic-evidence.json
```

Write the evidence file at the shown path before validating it and embed the completed JSON under `## Semantic evidence JSON` in the PR body. These commands are planned; no implementation test results are claimed by this document.

- [ ] Perform the fresh semantic review using `.agents/skills/review-semantic-change/SKILL.md`; inspect real caller behavior, provenance, multi-input aggregation, and lifecycle authority. Resolve every actionable finding against the current revision and rerun invalidated checks.
- [ ] Confirm the acceptance table below before marking the issue complete. Update the Issue/Project using the planning skill only when acceptance is merged; audit after writes. M7 as a whole remains incomplete because forecast and decision-support work is separate.

| Issue #60 acceptance | Required evidence |
|---|---|
| Seven named kinds distinguished | Task 3 corpus covers each; Task 5 source-backed public examples. Coverage gap is also exercised. |
| Detection separate from prediction/decision | Domain tests, architecture checks, read-only public boundary; no forecast or remediation code. |
| Suppression, review, lifecycle states | Task 4 transition/replay matrix and Task 5 read-only history; enum presence alone is insufficient. |
| Configurable, auditable thresholds | Canonical configuration, digest/provenance, exact boundary and changed-config identity tests. |
| Source and state evidence retained | Role-specific references, governing IDs, scope/as-of, complete coverage evidence and real HTTP/install drill-down. |

## Execution handoff

Recommended next action: implement slice A from current main after reviewing Task 1's semantic contract. Implement natively because the slices share input qualification and provenance interfaces; do not dispatch agents merely because this plan has multiple tasks. This plan authorizes no external deployment, data import, source correction, or procurement action.
