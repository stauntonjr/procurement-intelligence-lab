# Deterministic package planning implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline. Steps use checkboxes for tracking.

**Goal:** Satisfy Issue #205 with a pure physical planner and a clean-installed public CLI.

**Architecture:** Platform dataclasses describe implementations and explicit deployment selections.
The planner revalidates language-neutral compiler output against the existing catalog and compiler,
checks selected descriptor contracts/capabilities/configuration, and emits canonical plan bytes plus
SHA-256. Composition and file access remain outside the platform; no implementation executes.

**Tech stack:** Python 3.12 stdlib dataclasses, JSON, TOML, hashlib; pytest.

**Spec:** Issue #205 and ADR-022; detailed schema and decisions in
`docs/architecture/runtime-planning.md` (delivered with this slice).

## Global constraints

- Exactly twelve logical stages, in platform order; no domain branching or executable callbacks.
- Explicit deployment selection for every EXECUTE stage; none for EMPTY/PASSTHROUGH.
- Schema versions and contract references match exactly; profile ID/version pins match the manifest.
- Settings are immutable string pairs; descriptors declare required/optional keys. No secret resolution.
- Plans retain semantic references, checks and independent versions. Plans are not execution receipts.

## Review focus

- Duplicate JSON keys or TOML definitions must not silently overwrite an explicit selection.
- Malformed JSON values must yield typed diagnostics rather than Python runtime exceptions.
- Invalid unused registry entries must fail admission, even if another entry is compatible.
- Reordering registry entries, selections or settings must preserve plan bytes and hashes.
- Neutral stages must not mask missing providers or imply evidence/approval exists at runtime.

## Task 1: Contracts, validation and deterministic planning

Files: `platform/planning/{contracts,inputs,planner}.py`,
`tests/unit/test_package_planning.py`, `tests/planning_fixtures.py`, contract registry version metadata.

- [x] Add failing tests for real compiled procurement and a non-procurement package, all three modes,
  determinism, immutable records, exact versions, invalid/duplicate inputs, capability/config mismatch.
- [x] Run the tests and observe the missing planner failure.
- [x] Implement immutable descriptors/config/plan and strict pure loaders, then `plan_manifest`.
- [x] Run focused tests, including all five review-focus conditions; commit coherent implementation.

## Task 2: Public CLI, installed artifact and durable architecture

Files: `interfaces/plan_package.py`, `tools/package_smoke.py`, integration tests,
`docs/architecture/runtime-planning.md`, ADR-022, conformance, README, milestone map and handoff.

- [x] Add subprocess CLI tests for procurement/non-procurement success and typed malformed/failing inputs;
  observe failure before adding the CLI.
- [x] Implement `python -m procurement_intelligence_lab.interfaces.plan_package --manifest FILE
  --registry FILE --config FILE`; only file access occurs at this boundary.
- [x] Extend clean-wheel smoke using external planning fixtures, not packaged fake executors.
- [ ] Update architecture/status docs and run focused tests, package smoke, `make check`, challenges.
- [ ] Record exact-revision semantic evidence, independent review and required CI; merge only when green.


## Review correction

Independent review of `004fe75` found that duplicate/non-finite JSON diagnostics used the generic
`json` path and malformed contract versions lost registry source identity. Five real CLI cases
first failed their input-context assertions, then passed after loader errors retained their source
and registry-contract field context. This is a pre-merge acceptance correction, not a shipped
semantic defect. PhysicalPlan constructor validation was assessed as optional: the output-only
record is populated exclusively with immutable bytes and a computed string hash by the planner.
Final exact-revision commands/review are retained in the linked PR semantic evidence.
