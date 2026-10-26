# Durable RESOLVE Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Implement inline, then one independent final whole-branch review. Steps use checkbox syntax.

**Goal:** Implement #244's approved separate durable six-stage local job profile.
**Architecture:** Frozen platform dataclasses own pins/lifecycle/completion binding. Application runs the existing resolved prefix; Postgres atomically retains all evidence after fencing. Bootstrap is the composition root; a separate CLI preserves old five-stage v1 callers.
**Tech Stack:** Python3.12/3.13, stdlib domain, optional psycopg/Postgres, existing allowlisted codec and pytest/Hypothesis.
**Spec:** docs/superpowers/specs/2026-10-25-resolved-prefix-jobs-design.md, approved at36b9378 by the owner's subsequent “continue”.

## Global Constraints

- Recipe procurement.bom-local-resolved-prefix@1; capability local_resolved_prefix_jobs/v1; source/prefix/resolved archives are explicit prerequisites, old jobs are not.
- Fixed six actual stages; remaining six NOT_EXECUTED, package completion false. No new matching/authority policy, queue, lease, automatic retry or operational-agent permission.
- All runtime settings/context environment empty. Catalog/raw policy/pins immutable; profile-local arrival identity. Old IDs/wire/rejections/initialization remain compatible.
- Key1..256, text1..4096, graph16MiB/50,000nodes/depth64, catalog32KiB/256keys, history1..200; aware fixed-offset monotonic times, signed64bit counters.
- Same scope/key compares full request including raw catalog. First/current full receipts remain distinct. Unknown acknowledgement is not FAILED. Historical replay prepares no executor.
- Every applicable scenario needs positive evidence. No semantic-defect challenge absent an actually shipped defect; existing challenges remain.

## Review Focus

- Changed raw catalog with equal semantic identity must conflict under one request key, while separate jobs may share first-retained computation.
- Exact replay after a later retry cannot claim a newly current operation; all observed-version/current versus historical roles remain truthful.
- Stale writer and success/abandon races must fence before any source/result write, not merely before head update.
- Corrupt linked evidence or an internally consistent stale head must fail integrity validation rather than return success/not-found.
- Existing v1 data, graph bytes, IDs, CLI payloads and defaults must survive additive codec registration and archive helper extraction.

### Task 1: Typed pins, identity, lifecycle and complete binding

**Files:** platform/processing/resolved_contracts.py, resolved_binding.py, resolved_lifecycle.py, resolved_errors.py; ports/resolved_prefix_jobs.py; tests/resolved_job_fixtures.py; tests/unit/test_resolved_job_contracts.py, test_resolved_job_lifecycle.py, test_resolved_job_codec.py.
**Interfaces:** Produce PinnedResolvedPrefixDefinition(prefix, candidate_input, policy, resolution_metadata, recipe_id), ResolvedJobDefinition and distinct Resolved* commands/token/success/transition/receipt/view/history. Reuse existing enums/ArtifactArrival/JobFailure. Port methods match the old journal's semantics with resolved types.

- [ ] Write tests for raw/semantic catalog identity, exact namespaces, malformed direct construction, pins/settings/time/scope/counter boundaries, lifecycle parity, full completion substitution and allowlisted graph roundtrip.
- [ ] Run tests and retain expected missing-feature RED before production implementation.
- [ ] Implement new typed contracts, source-free validations, lifecycle and complete source/first-five/sixth/catalog/raw/result binding; add explicit resolved-job error codes and additive codec tags.
- [ ] Run `uv run --extra workflow pytest -q tests/unit/test_resolved_job_contracts.py tests/unit/test_resolved_job_lifecycle.py tests/unit/test_resolved_job_codec.py tests/unit/test_local_prefix_job_contracts.py tests/unit/test_local_prefix_job_lifecycle.py tests/unit/test_local_prefix_job_codec.py`.
  Expected: all pass, no skips. Commit.

### Task 2: Existing six-stage runner guard and application orchestration

**Files:** platform/execution/resolution_runner.py; application/resolved_prefix_job_admission.py, resolved_prefix_jobs.py, resolved_prefix_job_reader.py; bootstrap.py; tests/unit/test_resolved_job_execution.py.
**Interfaces:** Consume Task1 pins/port. Produce pin_resolved_prefix_job, ResolvedPrefixJobService, ResolvedPrefixJobReader; bootstrap builders prepare only the explicit recipe. run_resolved_prefix gains optional capture_guard passed directly to run_prefix.

- [ ] Write failing real-runner tests proving six stage invocations and guard rejection before STRUCTURE; input pin reconstruction must reject changes before claiming or constructing persistence.
- [ ] Implement application submit/execute/replay/failure/abandon and reader validation with existing runner and exact pinned metadata, keeping publication outside failure catch.
- [ ] Run `uv run --extra workflow pytest -q tests/unit/test_resolved_job_execution.py tests/contract/test_planned_resolved_bom_execution.py tests/unit/test_planned_bom_resolution.py`.
  Expected: pass with unchanged legacy execution. Commit.

### Task 3: Real Postgres journal and atomic archive integration

**Files:** adapters/postgres_resolved_prefix_jobs.py, postgres_resolved_job_writes.py; adapters/postgres_resolved_execution_archive.py; tests/contract/test_postgres_resolved_jobs.py, test_resolved_job_service.py.
**Interfaces:** Consume Task1 port and Task2 service. Produce explicit initialized PostgresResolvedPrefixJobs. Extract resolved archive _append_in_transaction(conn, completed, content); append's public result remains identical.

- [ ] Write failing real-Postgres contract tests for initialization independence, exact replay/conflicts, history, stale-head/corrupt-link checks and full receipt/raw-byte completion replay.
- [ ] Implement journal immutable tables/CAS heads, transaction-scoped typed reads and sanitized failures. Complete locks head, validates fence, writes source/prefix/resolved/full success atomically using existing archive ordering.
- [ ] Add races and faults: success-versus-abandon, same-key starts, stale success/failure, each publication checkpoint, loss before/after acknowledgement, prior prefix/resolved retention, historical outcome after later retry and failure-journal outage. Verify source-free recovery.
- [ ] Run with explicit disposable `PIL_TEST_POSTGRES_DSN`: `uv run --extra workflow pytest -q tests/contract/test_postgres_resolved_jobs.py tests/contract/test_resolved_job_service.py tests/contract/test_postgres_local_prefix_jobs.py tests/contract/test_postgres_local_prefix_job_completion.py tests/contract/test_postgres_resolved_execution_archive.py`.
  Expected: all pass, zero storage skips. Commit.

### Task 4: Separate CLI and public recovery/restart

**Files:** interfaces/resolved_processing_jobs.py; tests/integration/test_resolved_processing_jobs_cli.py; tests/contract/test_resolved_processing_jobs_public_main.py; docs/architecture/local-resolved-prefix-jobs.md; README.md.
**Interfaces:** Consume Task2/3 builders; expose init/submit/run/retry/abandon/show/history/result/content under only the new module, exact spec arguments/receipt roles and exit0/exit2 semantics.

- [ ] Write failing subprocess tests for admission-before-storage, six-stage result, malformed/cross-scope/profile IDs, source/config/catalog deletion, historical failure/abandon/current output, paging and no-overwrite export.
- [ ] Implement the new parser/projections. Preserve exact metadata on uncertain acknowledgement; no old CLI changes or implicit profile selection.
- [ ] Exercise process-death/restart and distinct current/first/embedded prefix receipt cases through actual shipped caller.
- [ ] Run `uv run --extra workflow pytest -q tests/integration/test_resolved_processing_jobs_cli.py tests/contract/test_resolved_processing_jobs_public_main.py tests/integration/test_processing_jobs_cli.py tests/contract/test_processing_jobs_public_main.py` with disposable Postgres.
  Expected: pass, zero storage skips. Commit.

### Task 5: Qualification, compatibility and durable evidence

**Files:** docs/development/evidence/issue-244/; affected handoff/map/ADR/docs; tests/public installed probe and compatibility fixtures as needed.
**Interfaces:** Produce exact-revision commands/scenario dispositions, clean built artifact and main-independent qualification, latest semantic evidence JSON and review package.

- [ ] Freeze baseline old public payload/graph/ID/rejection comparisons and compare the implementation candidate; source-free six-stage caller keeps original semantic outputs and abstentions.
- [ ] Run real public installed base/storage probes outside checkout on3.12/3.13, including no original source/config/catalog and every advertised new command. Build wheel and inspect actual import prefix/resources.
- [ ] Run `make check`, `make package-smoke`, and `make challenges` using the explicit owned Postgres environment. Expected: pass with zero storage skips; explicit unrelated browser/live skips are recorded.
- [ ] Validate latest semantic evidence with tools/validate_semantic_change.py; record exact argv, source/qualification revision and outcomes. Update accepted ADR/handoff/map/docs without broader completion claims. Commit.

### Task 6: One final review and protected delivery

**Files:** final review/receipt evidence and Issue244/Project state.
**Interfaces:** Consume qualified tree and exact review package. Produce reviewed correction disposition, protected merge, equal main tree and installed main proof.

- [ ] Dispatch exactly one independent final whole-branch reviewer on the most capable available model with spec/plan/rulings and Review Focus. Re-grade and record every finding/declined boundary; fix Important/Critical once with RED/GREEN and required requalification. No second reviewer or unrequested minor changes.
- [ ] Publish PR with exact-head semantic evidence; resolve/rebut actionable automated threads and wait for every required deterministic check.
- [ ] Merge through the normal protected path, verify exact reviewed/qualified versus main tree and installed main behavior. Close only244 when criteria are complete; synchronize Project/handoff/map and final audit.
- [ ] Preserve user/shared resources. Remove only owned worktree/container/temporary artifacts after durable receipts. Report exhaustive rulings and deferred minors; broader36/M3 stay open.
