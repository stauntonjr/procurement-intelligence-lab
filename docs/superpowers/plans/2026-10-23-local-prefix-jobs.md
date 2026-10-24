# Durable Local Prefix Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable local synchronous submission, explicit attempts and fenced recovery around the existing actual five-stage prefix without changing legacy execution or retention.

**Architecture:** Framework-independent frozen records own request identity, transitions and binding. An injected journal port publishes source/archive/current-attempt success in one Postgres transaction; a small application coordinator calls the existing runner. A separate trusted developer CLI reconstructs stored inputs for execution and uses validated evidence for recovery.

**Tech Stack:** Python stdlib dataclasses/Protocols, existing bounded SemanticCodec, optional psycopg/Postgres16, argparse, pytest; no new dependencies.

**Spec:** [Approved design](../specs/2026-10-23-local-prefix-jobs-design.md), owner-approved proposal `da09f989ddf1806d7e9877d7cf7c426e6fec5c37` on 2026-10-23. Decision #231 / [ADR-045](../../adr/045-local-prefix-jobs-and-fenced-attempts.md); implementation Issue #232, primary M1, native parent #36. Baseline main `87cc5ccb967e2063b348f90744aaafae741e66b1`.

**Plan status:** Owner-approved at revision `6dc1522` on 2026-10-23; implementation is tracked in #232; exact qualification/review/protected delivery receipts live there. Preserve established Native/inline execution with one independent final architecture/semantic review.

## Global Constraints

- Core owns semantics; adapters own mechanics. Use stdlib frozen dataclasses and Protocols; no DB/framework/procurement imports in neutral records/ports.
- Use only the already qualified actual INGEST-through-ASSERT prefix. All seven later declarations remain NOT_EXECUTED, including unvisited EMPTY declarations.
- This first job profile requires **empty settings for every config selection, including later unvisited stages**.
- Keep the **same original execution request and effective semantic context across attempts**. Attempt ID, ordinal, server start/end and command actor/time are separate durable journal evidence.
- Only the invocation receiving a newly acknowledged claim may execute. This per-call claim disposition is outside the immutable STARTED receipt.
- START (FIRST and RETRY share it) and ABANDON are command families. Compare complete canonical values, not digest-only equality; exact command replay returns historical evidence without applying a transition.
- Successful publication must be one transaction: validate current active attempt/fence and pinned request/output binding, retain original source evidence and completed-prefix binding, append the full current-attempt receipt, and advance the job head to SUCCEEDED.
- Initial lock order is job admission/head first, then source batches, then execution bindings; never hold these locks over executor I/O.
- After completion publication starts, **any unavailable/ambiguous acknowledgement leaves the caller uncertain**. Do not catch it and append FAILED.
- Reuse existing bounds: 16MiB graph payload, 50,000 nodes/depth64; metadata files 1MiB/32KiB; keys 1..256 UTF-8 characters with no surrounding whitespace; other identity/actor/reason text uses existing 1..4096-character bounds; positive exact signed64-bit versions/ordinals, nonnegative exact lengths/cursors; history default100/max200 with limit+1 evidence.
- DSN remains only in PIL_ASSERTION_ARCHIVE_DSN. Persist no credential, callback, raw exception text or arbitrary logs. Caller actor labels are provenance, not authentication.
- Preserve execute_package, planned_execution_archive, all old IDs/digests/wire formats and old workflow flags. New output separates job_journal_receipt, attempt_execution_receipt and retained_execution_receipt.
- No queue/listener/lease scheduler, timeout expiry, automatic retry/recompute, hard cancellation, later/neutral execution, new operational authority, model swap or production deployment. Broad #36 stays open.

## Review Focus

1. A START key reused as RETRY or with a changed actor/version must conflict, even after abandonment; Tasks1/3/6 test the full command family/payload.
2. Equal instants encoded with different offsets, and completion receipts with equal computations but different completion encoding, must remain distinct where the spec requires full canonical equality; Tasks1/2/4 exercise both.
3. A lost failure/start/success acknowledgement must not authorize execution or invent a terminal outcome; Tasks3/4/5/6 test fresh-process recovery and forbid side effects.
4. A late worker publishing after abandon→retry must be fenced before any source/result write; Tasks3/4 exercise actual concurrent transactions and both possible race winners.
5. Deleting original config/source must not break stored reads, while corrupt linked evidence must never become empty/not-found/success; Tasks2/4/6/7 cover these through the real public/artifact path.

---

## File structure and shared interfaces

All source paths below are relative to `src/procurement_intelligence_lab/`. Tests/tools/docs paths are repository-relative.

- New `platform/processing/{__init__,contracts,lifecycle,binding,errors}.py`: immutable identities/records; pure state transitions; request/output binding; typed local-job failures. No generic workflow framework.
- New `ports/local_prefix_jobs.py`: atomic journal protocol. New `adapters/postgres_local_prefix_jobs.py` owns connection/error/read orchestration; `adapters/postgres_local_prefix_job_writes.py` owns transaction-scoped writes. No business state rules hidden in SQL.
- New `application/local_prefix_job_admission.py`, `application/local_prefix_jobs.py`, `application/local_prefix_job_reader.py`: pin/admit; explicitly claim/run/publish; validated recovery, respectively.
- New `interfaces/processing_jobs.py` and `interfaces/processing_job_inputs.py`: CLI dispatch/projection and strict input documents. Bootstrap remains the visible composition root.
- Modify `platform/execution/runner.py` with an optional post-INGEST guard; modify `adapters/postgres_planned_execution_archive.py` to expose its existing append body as a transaction-sharing helper. Old public behavior remains identical.
- New `tests/local_prefix_job_fixtures.py`: synthetic actual-prefix inputs and deterministic clocks, not a fake successful runner. Separate unit/contract/integration suites below keep lifecycle, storage and public acceptance distinguishable.

Task1 defines these public records (all frozen) for downstream tasks. Constructors validate exact types and intrinsic invariants; derived IDs use existing canonical encoding with new `local-prefix-*` namespaces:

| Record / enum | Retained fields and role |
|---|---|
| ArtifactArrival | scope, event_id, source, expected_content_hash, expected_byte_length, announced_at |
| PinnedStageMetadata | stage, references, policy_version, schema_version; one ordered record per executed stage |
| PinnedPrefixDefinition | recipe_id, manifest bytes, registry, config, original request, normalization parameters, plan, stage_metadata; derived effective_context |
| JobDefinition | arrival, idempotency_key, definition; derived scope/job_id/request_digest |
| JobStatus / AttemptStatus / StartIntent / TransitionKind | SUBMITTED/RUNNING/SUCCEEDED/FAILED/ABANDONED; STARTED/SUCCEEDED/FAILED/ABANDONED; FIRST/RETRY; SUBMITTED/STARTED/SUCCEEDED/FAILED/ABANDONED |
| StartAttemptCommand | scope, job_id, command_key, actor, expected_version, intent |
| AbandonAttemptCommand | scope, job_id, command_key, actor, expected_version, attempt_id, reason |
| AttemptToken | scope, job_id, attempt_id, ordinal, fence; opaque publication right validated against active evidence |
| JobFailure | stable ErrorCode, ErrorCategory, allowlisted diagnostic; no arbitrary metadata |
| AttemptSuccess | full CompletedPrefixSnapshot for this attempt plus ExecutionArchiveReceipt for first retention |
| JobTransition | scope/job_id, per-job sequence, version, kind/status, recorded_at, optional typed command, attempt token, failure or success as required by kind; derived record_id |
| JobJournalReceipt | immutable transition acknowledgement, exposing transition identity/version/sequence |
| StartClaim | receipt, token, newly_claimed; per-call disposition, not persisted as part of STARTED receipt |
| JobView | immutable definition, latest validated receipt; status/version derived from it |
| JobHistoryPage | scope/job_id, after_sequence/limit, receipts, has_more/next_after_sequence |

Positive versions/ordinal/fence begin at1; per-job transition sequence begins at1. Job IDs derive from exact `(scope,idempotency_key)`; attempt IDs derive from `(scope,job_id,ordinal)`. Fence advances on start and abandonment, never wraps; only the active token may publish. Overflow fails typed before writes. Other acknowledgements never claim a new invocation right.

## Task 1: Immutable contracts, pure lifecycle and typed failures

**Files:** Create the five `platform/processing` files, `ports/local_prefix_jobs.py`, `tests/local_prefix_job_fixtures.py`, `tests/unit/test_local_prefix_job_contracts.py`, `tests/unit/test_local_prefix_job_lifecycle.py`; modify `platform/semantics/errors.py` only for seven stable ErrorCode values.

**Interfaces:**
- `PinnedPrefixDefinition.from_prepared(prepared:PreparedPrefix, *, recipe_id:str, normalization_parameters:tuple[tuple[str,str],...])->PinnedPrefixDefinition` stores neutral selected metadata, never executors. `effective_context` reproduces current `PreparedPrefix.context` exactly.
- `validate_definition(definition:PinnedPrefixDefinition)->None`; `validate_completion(job:JobDefinition, completed:CompletedPrefixSnapshot, content:bytes)->None` in binding.py validate full plan/context/source/policy/output and expected actual bytes. Current deployment support is injected later.
- `start_transition(view:JobView, command:StartAttemptCommand, *, now:datetime)->JobTransition`; `abandon_transition(view:JobView, command:AbandonAttemptCommand, *, now:datetime)->JobTransition`; `failure_transition(view:JobView, token:AttemptToken, failure:JobFailure, *, now:datetime)->JobTransition`; `success_transition(view:JobView, token:AttemptToken, success:AttemptSuccess, *, now:datetime)->JobTransition`. Storage handles serialization/replay lookup before invoking these pure policies.
- `LocalPrefixJobs` Protocol: `check_ready()->None`; `submit(job:JobDefinition, *, now:datetime)->JobJournalReceipt`; `load(scope:StateScope, job_id:str)->JobView`; `start(command:StartAttemptCommand, *, now:datetime)->StartClaim`; `abandon(command:AbandonAttemptCommand, *, now:datetime)->JobJournalReceipt`; `fail(token:AttemptToken, failure:JobFailure, *, now:datetime)->JobJournalReceipt`; `complete(token:AttemptToken, completed:CompletedPrefixSnapshot, content:bytes, *, now:datetime)->JobJournalReceipt`; `history(scope:StateScope, job_id:str, *, limit:int=100, after_sequence:int=0)->JobHistoryPage`; `content(scope:StateScope, job_id:str)->bytes`.
- New `JobContractError`, `JobConflictError`, `JobBusyError`, `JobFencedError`, `JobNotFoundError`, `JobIntegrityError`, `JobUnavailableError` subclass SemanticContractError. Codes respectively `pil.input.local_prefix_job_invalid`, `pil.policy.local_prefix_job_conflict`, `pil.policy.local_prefix_job_busy`, `pil.policy.local_prefix_job_fenced`, `pil.input.local_prefix_job_not_found`, `pil.infrastructure.local_prefix_job_integrity_invalid`, `pil.infrastructure.local_prefix_job_unavailable`; category follows each prefix. Existing execution failures preserve their codes/categories.

- [ ] Write `test_job_identity_compares_full_request`, `test_all_config_settings_rejected`, `test_definition_derives_original_effective_context`, `test_transition_matrix_and_historical_command_payload`, `test_counter_time_and_scope_boundaries`. Parameterize empty/one/many, duplicate/conflict/null, bool/fractional/negative/overflow, source observation ≤ pinned capture/context start ≤ submission server time, future announcement, regressing clock, cross-scope and different encoded offsets. Pin START FIRST/RETRY shared-family conflicts and immutable semantic context.

  ```python
  assert job.job_id == changed_policy_same_key.job_id
  assert job.request_digest != changed_policy_same_key.request_digest
  assert definition.effective_context == prepared.context
  assert canonical(definition.effective_context) == canonical(prepared.context)
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_local_prefix_job_contracts.py tests/unit/test_local_prefix_job_lifecycle.py`; expect RED for absent records/policies.
- [ ] Implement records, exact canonical validators and transition signatures above. Enforce the full approved state matrix, strict int64/text/time/bounds, recipe/plan consistency and shape-specific failure/success fields; no wall-clock reads inside domain records.
- [ ] Run the same command plus `uv run --extra workflow python tools/check_architecture.py` using the task cache; expect PASS. Commit `feat: define local prefix job identities and fenced lifecycle`.

## Task 2: Portable pinned-input and journal codec

**Files:** Modify `bootstrap.py::archive_codec`; create `tests/unit/test_local_prefix_job_codec.py`; preserve `adapters/semantic_codec.py` graph schema1 and existing golden fixtures. No codec-format change is planned.

**Interfaces:** Existing `SemanticCodec.dumps/loads/node_digest` remain unchanged. Explicitly register Task1 records/enums plus ExecutionRequest, ContractRef, ImplementationDescriptor/Registry, StageSelection and ImplementationConfig. Do not register PreparedPrefix, executors or StartClaim.

- [ ] Write `test_actual_pinned_definition_and_terminal_receipt_round_trip`, `test_all_journal_roots_reject_malformed_linkage`, `test_legacy_archive_wire_is_byte_identical`. Assert exact manifest/plan bytes, encoded offsets, IDs and both full current/first-retained receipts; reject unknown records, mutable nested values, malformed enum/type/root/checksum, excessive graph depth/nodes/bytes and nonempty unvisited settings even with recomputed outer checksums.

  ```python
  restored = codec.loads(codec.dumps(success_transition))
  assert canonical(restored) == canonical(success_transition)
  assert restored.success.completed.execution.receipt_digest == current.receipt_digest
  assert restored.success.retained.receipt_id == first_retained.receipt_id
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_local_prefix_job_codec.py`; expect RED from unregistered input/journal records.
- [ ] Add finite registrations only; persisted constructor/validation errors become JobIntegrityError at the journal adapter boundary. Never fall back to pickle, dynamic imports, dict-only graphs or storing callbacks.
- [ ] Run the new suite plus `tests/unit/test_archive_codec.py tests/unit/test_planned_execution_archive_codec.py`; expect PASS including the existing exact golden snapshot wire/hash. Commit `feat: encode pinned local jobs and attempt evidence`.

## Task 3: Durable submission, explicit claims and abandonment

**Files:** Create the two Postgres job adapter files and `tests/contract/test_postgres_local_prefix_jobs.py`; modify bootstrap with `build_local_prefix_jobs(dsn:str)->LocalPrefixJobs`; reuse `tests/postgres_fixtures.py::archive_dsn`.

**Interfaces:** `PostgresLocalPrefixJobs(archive:PostgresPlannedExecutionArchive, codec:SemanticCodec)` implements the port plus explicit `initialize()->None`. Its connection boundary translates unavailable DB/driver errors into sanitized JobUnavailableError, preserving typed conflict/fenced/integrity errors. All helper writes receive an existing connection and never commit independently.

- [ ] Provision only a task-owned disposable pinned Postgres16 container on an available loopback port. Record its exact ID/label and PIL_TEST_POSTGRES_DSN; preserve shared containers. Missing opt-in or skipped storage tests is not qualification.
- [ ] Write real DB tests for explicit capability initialization/readiness, atomic arrival+job+SUBMITTED, same-key exact replay versus full-payload conflict, same-event/different-arrival conflict across jobs, distinct keys and restart. Spy source access to prove submit does none. Force a test-only digest collision to prove full equality checks.
- [ ] Write barrier-driven concurrent same/different start-key tests: one active token, one `newly_claimed=True`, immutable receipt on replay, wrong intent/version/actor conflicts. Cover fail/abandon→explicit RETRY, late old abandon replay, clock/counter overflow, head/command/transition corruption and rollback of incomplete journal writes. No timing-based sleeps.

  ```python
  assert sum(claim.newly_claimed for claim in concurrent_same_command) == 1
  assert len({claim.receipt.transition.record_id for claim in concurrent_same_command}) == 1
  assert jobs.load(scope, job_id).status is JobStatus.RUNNING
  ```
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_postgres_local_prefix_jobs.py`; expect RED for missing capability/adapter, not skipped DB tests.
- [ ] Implement `pil_local_prefix_job_meta` version1; immutable arrival/job/command/transition payload tables with checksums and scoped uniqueness/FKs; mutable `pil_local_prefix_job_heads` with current version/sequence/status/attempt/fence/time. Use job admission serialization before head creation and row lock after creation. Command uniqueness is `(scope,job_id,family,key)` with family START or ABANDON, full canonical payload check before stale-version checks. Projection must agree with latest immutable evidence; new writes call Task1 policies. Explicit init requires archive1 and planned_prefix_archive/v1 and alters no existing tables. Reads never initialize.
- [ ] Implement scoped load/history with root/identity/checksum/full-request/command/head validation. History uses per-job sequence, exact bounds, limit+1 and validation of returned evidence; do not claim unseen history inspected. Different-scope IDs return typed not-found. Journal connection loss after a start/fail/abandon commit is ambiguous; exact-key/fresh lookup recovers evidence, never claims execution permission retroactively.
- [ ] Run the suite with real DB plus archive/review/dependency contract suites; expect PASS. Commit `feat: persist local job submissions and explicit fenced attempts`.

## Task 4: Atomic successful completion and stale-writer exclusion

**Files:** Modify `adapters/postgres_planned_execution_archive.py`, both job adapter files; create `tests/contract/test_postgres_local_prefix_job_completion.py`; retain old archive tests unchanged.

**Interfaces:** Extract `PostgresPlannedExecutionArchive._append_in_transaction(conn:psycopg.Connection[dict[str,Any]], completed:CompletedPrefixSnapshot, content:bytes)->ArchivedPrefix`; public append wraps the helper in its existing check/connection semantics. Task1 port `complete` returns the job receipt whose transition.success stores full current completed snapshot and first-retained archive acknowledgement.

- [ ] Write `test_complete_binds_current_receipt_source_archive_and_job_atomically`, `test_same_attempt_changed_completion_conflicts`, `test_distinct_jobs_share_computation_not_current_receipt`. Also reject any new run/retry/abandon after positively recorded success. First retain a computation outside a job, then complete an equal computation with a different completion time; preserve the old full archive receipt while recovering the exact current attempt receipt.
- [ ] Write DB-trigger rollback tests failing after source insert, archive insert and terminal insert; fresh connections must observe no new source/result/terminal writes. Existing evidence may remain, but must not imply this attempt succeeded. Test exact same completion replay, changed bytes even on an existing digest, recomputed-checksum corruption and missing current/retained/source linkage.
- [ ] Write deterministic two-connection complete-vs-abandon and fail-vs-abandon races with barriers around lock acquisition. Assert the winner's immutable terminal state; if abandoned, stale completion writes no source/result evidence, including after a new retry starts. Inject a post-commit acknowledgement failure, then verify full success through a fresh connection without appending FAILED.

  ```python
  with pytest.raises(JobFencedError):
      jobs.complete(old_token, completed, content, now=later)
  assert fresh_jobs.load(scope, job_id).version == retry_claim.receipt.transition.version
  assert new_source_and_archive_row_counts() == before_counts
  ```
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_postgres_local_prefix_job_completion.py`; expect RED from missing atomic completion/fencing.
- [ ] Extract the archive helper preserving exact old validation/locks/wire/IDs. In complete: lock/validate head and token first, validate full candidate/arrival binding, then call archive helper under the same transaction, store AttemptSuccess, append terminal transition and update head. Validate exact replay before returning; equal computation alone is insufficient for same-attempt replay. No source/result write before fence validation; no separate append/finish commits. Bound success reads validate the current snapshot and referenced first archive/source evidence.
- [ ] Run both job suites and `tests/contract/test_postgres_archive.py tests/contract/test_postgres_planned_execution_archive.py`; expect PASS and unchanged legacy identities. Commit `feat: commit job success with source and execution evidence atomically`.

## Task 5: Stored-input execution, capture guard and truthful recovery

**Files:** Create the three application files; modify `platform/execution/runner.py`, bootstrap; create `tests/contract/test_local_prefix_job_service.py`; preserve actual runner/default/archive tests.

**Interfaces:**
- Add `run_prefix(prepared:PreparedPrefix, *, clock:Callable[[],datetime], capture_guard:Callable[[CapturedOutput],None]|None=None)->PrefixExecution`; invoke guard after existing INGEST provenance checks and before STRUCTURE, no second capture. Default None preserves old execution/projection.
- `pin_local_prefix_job(prepared:PreparedPrefix, arrival:ArtifactArrival, idempotency_key:str, *, normalization_parameters:tuple[tuple[str,str],...], now:datetime)->JobDefinition` performs complete pure admission, selects recipe `procurement.bom-local-prefix@1` and does no journal/source I/O.
- `LocalPrefixJobService(journal_factory:Callable[[],LocalPrefixJobs], prepare_stored:Callable[[PinnedPrefixDefinition],PreparedPrefix], content_store:ArtifactContentStore, validate_completed:Callable[[CompletedPrefixSnapshot],None], clock:Callable[[],datetime])`: `submit(job:JobDefinition)->JobJournalReceipt`; `execute(command:StartAttemptCommand)->JobExecutionResult`; `abandon(command:AbandonAttemptCommand)->JobJournalReceipt`. FIRST/RETRY is in the command, not inferred from state.
- `JobExecutionResult(receipt:JobJournalReceipt,command_receipt:JobJournalReceipt,historical:bool,observed_version:int)` is an application response, never persisted as immutable acknowledgement. The journal also exposes read-only `lookup_command(command:StartAttemptCommand|AbandonAttemptCommand)->JobJournalReceipt|None` for replay before runtime preparation.
- `LocalPrefixJobReader(journal:LocalPrefixJobs, validate_completed:Callable[[CompletedPrefixSnapshot],None])`: `show(scope,job_id)->JobView`; `history(scope,job_id,*,limit=100,after_sequence=0)->JobHistoryPage`; `result(scope:StateScope,job_id:str)->AttemptSuccess`; `content(scope:StateScope,job_id:str)->bytes`. The show/history scope and job types follow the port; result/content require SUCCEEDED and domain validation.
- Bootstrap adds `build_local_prefix_job_service(*,clock:Callable[[],datetime],journal_factory:Callable[[],LocalPrefixJobs])->LocalPrefixJobService`, `build_local_prefix_job_reader(dsn:str)->LocalPrefixJobReader`. Its stored-preparation callback reconstructs BomNormalizationPolicy from retained canonical parameters and builds only the supported five concrete adapters sharing one MemoryArtifactContent. Validate recipe/versions/resolved metadata/effective context exactly; no input-driven imports/current config files/fallback.

- [ ] Write actual-runner tests counting five real invocations, preserving null/conflicting/duplicate rows, zero/negative/fractional and each/dozen/currency behavior. Compare original IDs/default prefix output under identical semantic inputs; explicit retry has a later attempt clock but identical semantic context and claims. Every new claim executes all five stages, no archive-cache shortcut.
- [ ] Write `test_changed_source_fails_immediately_after_capture`, `test_submit_and_replayed_start_never_capture`, `test_unsupported_stored_recipe_does_not_claim`, `test_prepublication_failure_can_be_recorded_but_publication_ambiguity_cannot`. Forbid source/STRUCTURE/archive calls as applicable; preserve original stable execution code/category with an allowlisted diagnostic. Inject malicious str(exc)/DSN text and unknown programmer failures; persisted/public diagnostics must contain none of it.

  ```python
  assert calls == [StageId.INGEST]  # mismatched arrival expectation
  assert jobs.load(scope, job_id).status is JobStatus.FAILED
  assert source_archive_rows() == []
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_local_prefix_job_service.py`; expect RED for missing coordinator/capture guard.
- [ ] Implement submit by calling prepare_stored(job.definition) and comparing its complete retained metadata/context before lazy journal construction/readiness, then atomic submit. Execute loads stored definition, validates current supported deployment before claiming, then start acknowledgement; replay returns recorded outcome without source/executor I/O. Newly claimed run invokes guarded real runner, validates completed snapshot and bytes. Catch/classify only the pre-publication block to append failure; completion publication is outside that catch. A failed failure append remains uncertain; a fenced old writer cannot overwrite the winner. Busy/replayed failed outcomes are explicit typed failures, never success projections.
- [ ] Implement source/config/executor-free reader and abandonment delegation. Validate all returned current/retained domain evidence. Run new suite plus `tests/contract/test_archived_planned_execution.py tests/contract/test_package_document_executors.py tests/unit/test_package_execution.py tests/unit/test_package_execution_contracts.py`; expect PASS. Commit `feat: execute pinned local jobs with explicit recovery semantics`.

## Task 6: Strict developer CLI and actual restart/crash acceptance

**Files:** Create the two interface files, `tests/integration/test_processing_jobs_cli.py`, `tests/contract/test_processing_jobs_public_main.py`; reuse strict execution-input helpers and non-overwriting export mechanics without changing old interfaces.

**Interfaces:** `python -m procurement_intelligence_lab.interfaces.processing_jobs` implements init/submit/run/retry/abandon/show/history/result/content. Submit: positional source plus `--arrival --context --manifest --registry --config --normalization-policy --idempotency-key`; scope comes from exact arrival/context agreement. Arrival JSON has exactly event_id, expected_content_hash, expected_byte_length, announced_at. All other commands except init use `--scope --job-id`; run/retry also require `--command-key --actor --expected-version`; abandon adds `--attempt-id --reason`. History uses `--limit`/`--after-sequence`; content requires `--output`. No current input-file flags on run/retry/reads. `processing_job_inputs.parse_arrival(raw:bytes, source:SourceReference)->ArtifactArrival` and `parse_expected_version(raw:str)->int` enforce exact bounded input.

- [ ] Write real subprocess compile/init/submit→run→restart→show/history/result/content with isolated Postgres. Delete source and every original metadata/config/policy file before recovery. Assert actual five events/twelve entries, exact current/retained receipts, original source-reader compatibility, exported bytes and no-overwrite. Verify same/different submit keys, paginated transitions and late historical command acknowledgement plus current observed version.
- [ ] Add public malformed argument/Unicode/duplicate-key/nonfinite/missing/future/cross-scope/numeric/oversize/settings cases, missing backend/capability, source change then restored bytes plus explicit retry, terminal success rejection and corrupt linked evidence. Errors: exit2, JSON stderr, empty success stdout; metadata show exit0 with truthful status/completion. The new receipt projection removes only legacy workflow booleans; old caller JSON stays identical.
- [ ] Write actual public-main fault tests using injected adapter wrappers and real DB: commit then raise on submit/start/fail/complete/abandon; fresh subprocess lookup shows the actual committed state. For process death, launch a test-only child harness invoking public main with a real runner, signal a pipe after durable STARTED or committed success, block there, then terminate only that child. Restart retains RUNNING or SUCCEEDED as appropriate; abandon/retry fences its old token. No production fault flags, arbitrary sleeps or shared service interruption.

  ```python
  assert failed.returncode == 2 and failed.stdout == ""
  assert json.loads(recovered.stdout)["status"] == "SUCCEEDED"
  assert json.loads(result.stdout)["attempt_execution_receipt"] == expected_current
  assert exported.read_bytes() == original_content
  ```
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/integration/test_processing_jobs_cli.py tests/contract/test_processing_jobs_public_main.py`; expect RED for absent module/commands.
- [ ] Implement bounded strict parsers and projections inside the sanitized exception boundary. Read DSN only via configured_dsn; explicit init initializes only local_prefix_jobs/v1 after prerequisites. Add `job_journal_receipt`, full `attempt_execution_receipt`, `retained_execution_receipt`; command replay marks historical acknowledgement and current observed version without mutating old receipt. Empty/unknown result never fabricates success. Reuse export_content; source paths are not opened by request/arrival parsing.
- [ ] Run the new suites and all existing execute/archive/review/query/replay CLI suites with actual Postgres; expect PASS. Commit `feat: expose durable local processing jobs and restart recovery`.

## Task 7: Clean artifact, semantic evidence and protected delivery

**Files:** Create `tools/package_local_prefix_jobs_probe.py`, `docs/architecture/local-prefix-jobs.md`; modify `tools/package_smoke.py`, README, execution/archive docs, handoff and milestone map. Create canonical latest-revision semantic evidence for #232 as a PR-body JSON artifact.

**Interfaces:** Installed probe uses stdlib and actual installed module commands outside the checkout, with DSN solely from environment and isolated synthetic input copies. Integrate a fresh unique schema in package_smoke exactly like the existing planned archive probe. Output a small JSON evidence result; no DSN/log dumping.

- [ ] Write installed base-wheel missing-storage and optional-storage submit/run/delete/restart/result/export probes first. Run against clean baseline main87cc5cc wheel; expect RED for absent processing_jobs. Capture old default execution digest under exact source/context/config and require candidate equality; preserve all existing package probes and legacy golden wire tests.
- [ ] Qualify clean candidate base/storage wheels: source-free reads after deleting all input files, manual failure/retry/abandon history, exact current/first-retained distinction, old-reader equality and actual byte export. Base wheel returns typed missing-extra failure before capture. No editable install, checkout-import acceptance or opt-in skips promoted to proof.
- [ ] Document capability prerequisites, all commands, lifecycle/fences/manual retry, historical replay, expected bytes, atomic success/ambiguous acknowledgements, bounds/errors and exclusions. Update branch-versus-main handoff; #36 and broader Issues remain open. No model/algorithm benchmark claim is needed because none changed.
- [ ] Seal source and run `UV_CACHE_DIR=/tmp/pil-uv-cache make check-fast`, `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache make check`, `... make package-smoke`, and `... uv run --extra workflow python tools/run_challenges.py --verify-known-bad --results /tmp/pil-local-prefix-jobs-challenges.json`. Expect all required suites and unchanged coverage ratchet to pass, genuine DB/artifact tests executed and all public/known-bad challenge oracles satisfied. Browser/live skips remain explicitly outside this local claim.
- [ ] Obtain one fresh whole-branch semantic/architecture review of exact spec/plan/current revision; resolve material findings and rerun invalidated checks. Use applicable implement-domain-logic/add-adapter/test-public-interface/release-smoke/review-semantic-change/run-agent-challenges skills during execution. A discovered shipped defect needs its own regression/challenge; an unshipped gap does not become a fabricated shipped defect.
- [ ] Record authoritative inputs/output, exact scope/time/policy, retained evidence and typed failures, all seven scenario dispositions, exact commands and latest review in schema-valid semantic JSON. Validate using tools/validate_semantic_change.py and embed under `## Semantic evidence JSON` in PR body. No completion claim with missing public/DB/artifact evidence.
- [ ] Publish primary M1 PR: Closes #232 only for complete bounded acceptance; Closes #231 only for approved decision/spec/plan artifacts. Part of #36/#13/#21/#33/#35/#37/#75. Required deterministic checks and edited-body contract must pass; resolve/rebut arriving actionable review threads; no protection bypass or merge with pending/failing checks.
- [ ] After authorized merge, verify identical tested tree and actual merged-main public submit/run/restart/result/export using merged-revision config/context. Update Issue/Project receipts and durable handoff/map, perform roadmap/structural audits separately, and remove only the exact task-owned Postgres container. No deployment, general queue processing or broad #36 completion claim.

## Self-review and execution handoff

All spec sections map to tasks: arrival/pinning/identity/time and policy to1; codec/bounds to2;
submission/replay/CAS/failure/abandonment/history to3; full current/retained binding and transaction/
fence races to4; actual execution/admission/capture/failure ambiguity/read validation to5;
public errors/restart/process death to6; installed artifact/legacy/full qualification/review/delivery
to7. Review Focus cases have named owners and executable assertions. Task3 may build durable
non-success lifecycle independently; Task4 is the required atomic-success gate before Task5/6
can qualify real successful execution. No partial adapter is advertised as a runtime capability.

The seven tasks share records, transaction helpers and receipt projections. Preserve Native/inline
execution with one independent final review, as in the preceding approved archive plan. The owner approved this plan at `6dc1522` and instructed implementation on 2026-10-23.
Execution progress is recorded in the task ledger; no runtime acceptance is implied by approval.
