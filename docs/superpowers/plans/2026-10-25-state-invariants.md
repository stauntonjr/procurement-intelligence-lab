# State construction invariants implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for inline execution with one independent final review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Execution receipt:** Qualification/review are retained under issue-118 evidence. Issue118 carries the authoritative postmerge main-installed/Project/cleanup receipt for terminal Task3 completion; checkboxes here preserve the branch checkpoint.

**Goal:** Complete #118's existing constructor contract and its acceptance evidence.

**Architecture:** Domain dataclasses own intrinsic validity. One private aware-time guard serves both constructors and public helpers. No new domain policy or platform topology.

**Tech Stack:** Python 3.12+, dataclasses, Decimal, pytest/Hypothesis, existing public challenge runner.

**Spec:** docs/superpowers/specs/2026-10-25-state-invariants-design.md; Issue #118; ADR-020.

## Global constraints

- Quantities are finite nonnegative Decimal values; zero/fractions/overages remain valid.
- Pair identity includes canonical key and every StateScope field; missing observation remains None/UNKNOWN.
- As-of requires tzinfo and non-None utcoffset. Preserve valid offsets, evidence, existing outputs and ValueError compatibility.
- Keep intrinsic failures deterministic; use existing TemporalContractError for invalid timestamps.
- No authority, aggregation, fresh pipeline/job, anomaly-classification or production change.
- C008 stays executable; every repaired shipped defect gets its public regression/challenge oracle.
- Protected delivery, main acceptance, Issue/Project audit and only owned cleanup complete the slice.

## Review focus

- Offsetless tzinfo and empty helpers reject at their actual public boundary.
- All five observed components and expected quantity reject invalid values independently.
- Large valid/nonnegative component values and overages remain observations, with no invented sum constraints.
- Different valid record timestamps/offsets remain legal; scope equality includes version.
- Missing observation and empty evidence retain different semantics; no synthetic completeness.

### Task 1: Contract and regression oracle

**Files:** tests/regression/test_state_invariants.py; this spec/plan; docs/development/evidence/issue-118/.
**Interfaces:** existing ExpectedRequirement, ObservedProcurement, ExpectedObservedState, expected_requirements, compare_expected_observed public APIs, unchanged signatures.

- [x] Run the existing focused state/governed-state baseline.
- [x] Add parameterized/property coverage for every quantity, nonfinite/negative/zero/fractional/overage, evidence, each scope axis/key, missing/partial observations and offset preservation.
- [x] Add `test_state_boundaries_reject_offsetless_timezone` for both constructors and both empty-input helpers. Assert TemporalContractError with timezone-aware message. Run it and retain the expected RED.
- [x] Record exact semantic contract and seven scenario-family dispositions before changing source.
- [x] Commit contract/tests; no product code yet.

### Task 2: Minimal guard and challenge

**Files:** src/procurement_intelligence_lab/domains/procurement/state.py; evals/development_agents/challenges/C031.json; tools/run_challenges.py; docs/adr/020-expected-observed-state.md.
**Interfaces:** private `_require_aware(as_of: datetime) -> None`; existing TemporalContractError. Existing four public signatures unchanged.

- [x] Add private guard requiring `as_of.tzinfo is not None` and `as_of.utcoffset() is not None`; use it at both constructors and both helpers.
- [x] Rerun RED cases and complete focused state/governed-state suite; preserve all valid outputs.
- [x] Add C031 with introducing SHA discovered from history, mutation weakening only the offset check, and intended `DID NOT RAISE` failure. Advance explicit catalog count to31; keep C008 intact.
- [x] Run C008/C031 with known-bad verification; validate all manifests.
- [x] Update ADR-020 intrinsic boundary and commit.

### Task 3: Qualification, review and protected delivery

**Files:** docs/development/evidence/issue-118/; docs/project/handoff.md; docs/development/milestone-map.md; tests/integration/test_state_installed.py or equivalent retained installed command.
**Interfaces:** clean wheel exports the same constructors/helpers; known-bad public-oracle report has no agent-quality score.

- [x] Run actual clean installed public constructors/helpers outside checkout, including offsetless rejection, valid offsets, evidence, pair mismatch and overage preservation; run package-smoke.
- [x] Run make check with explicit task-owned real Postgres and unchanged coverage ratchets; run all31 challenges and known-bad equivalents. Inspect failures/skips.
- [x] Obtain one independent whole-branch architecture/semantic review at exact revision; resolve/rebut findings, retain RED/GREEN for fixes and rerun invalidated checks.
- [x] Record schema-valid latest-revision semantic evidence, review disposition, commands, public proof and advisory503/direct Project audit distinction. Update handoff/map; preserve broader open work.
- [ ] Open normal PR linking M4/#118, wait for required checks/resolved threads and merge without bypass. Verify main runtime tree matches qualification and installed proof.
- [ ] Close #118 only on main acceptance; set Project Done, audit/read back full Project, retain terminal task receipt and remove only owned test resources/worktree.

## Self-review

All Issue criteria map to Tasks1/2 (constructors/properties/overages/C008) and3 (ADR/handoff/qualified delivery). The shared API signatures do not change; all five review inputs have named coverage in Task1 and installed qualification in Task3. The owner authorized the concrete #118 contract; this plan introduces no new product-policy choice.
