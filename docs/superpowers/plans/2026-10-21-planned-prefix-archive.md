# Completed Planned-Prefix Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atomically retain actual planned-prefix execution and source evidence, then recover it in a fresh process without the original source or executors.

**Architecture:** A frozen completed-prefix binding and neutral port sit outside the runner. An application coordinator admits the runtime, checks storage readiness, runs five stages once and submits one atomic append. PostgreSQL reuses the existing source archive transaction; bootstrap registers portable types and injects policy validators and lazy storage construction.

**Tech Stack:** Python3.12+, frozen stdlib dataclasses/Protocols, existing typed graph codec, optional psycopg/Postgres16, pytest/ruff/pyright. No new runtime dependency, ORM, queue or orchestration framework.

**Spec:** [Approved design](../specs/2026-10-21-planned-prefix-archive-design.md), approved decision #228/ADR-044; implementation #229, primary M2, parent #37. Design approved at `50a204c`; baseline main `8e72f87`. This written plan awaits review before product changes. Preserve native/inline execution with one fresh final reviewer.

## Global Constraints

- Retain actual INGEST-through-ASSERT only; all twelve declarations remain visible and seven later entries remain NOT_EXECUTED. Prefix completion is never full-package completion.
- Use exact scope plus execution_digest; compare canonical computation, snapshot/policy parameters and bytes. Only server completed_at may differ on retry; retain the first committed full receipt and sequence.
- Every execute invocation still runs five stages. No attempt journal, lookup-before-execution cache, request exactly-once guarantee, automatic retry, new authority policy or wider-stage execution.
- Source snapshot/content/claim membership and execution binding commit in one transaction. Lost acknowledgement does not prove rollback. Never emit success before retention acknowledgement.
- Explicit `planned_prefix_archive/v1` initialization requires supported existing archive1; do not migrate or modify old archive/review/dependency/approved-correction capabilities, rows, IDs or default callers.
- Use `["bytes-hex", "lowercase even-length hex"]`, including empty bytes; preserve16MiB wire/50,000nodes/depth64, finite allowlists and old snapshot wire bytes. No pickle or imports driven by data.
- History: default100, maximum200; positive integer limit/nonnegative exclusive cursor; evidenced has_more/next_after_sequence, no invented total count. Exact scoped reads and non-overwriting source export.
- Current execution_receipt and first retained_execution_receipt are distinct in opt-in archival output. Keep default ephemeral output and durable_run_journal_updated/result_cache_updated=False unchanged.
- Domain validation is injected; core/ports cannot import procurement or PostgreSQL. DSN comes only from existing environment configuration and never appears in output/errors/provenance.
- Preserve original claims, unknown/null versus zero, empty batch evidence, duplicates/conflicts, exact timestamp offsets and all legacy archive/review/replay behavior.

## Review Focus

1. A retry with equal computation and a different completion encoding must retain the original receipt; changing any other encoded data must not alias that retry.
2. Receipt, source snapshot, auxiliary mention claims and retained policy parameters can each be independently well-formed but mutually inconsistent; reject their binding before persistence and on read.
3. Driver absence, unsupported runtime or missing storage capability must fail before source access; recovery must not accidentally construct or invoke current executors/configuration.
4. Failure after source rows are staged, or after commit but before acknowledgement, must not become partial success, a false rollback claim or a second committed binding on retry.
5. Exactly-full history pages and concurrent new rows must not fabricate completeness, cross scope or corrupt the exclusive cursor; old source readers must still admit the new source snapshots.

## File and interface map

Source paths below are relative to `src/procurement_intelligence_lab/`.

| Unit | Responsibility |
|---|---|
| `platform/execution/archive.py` | New frozen binding, retained acknowledgement/result/page, exact computation comparison and intrinsic bounds |
| `platform/execution/contracts.py` | Expose canonical computation payload without changing execution_digest |
| `ports/planned_execution_archive.py` | Readiness/atomic append/scoped load/history/content Protocol |
| `adapters/semantic_codec.py`, `bootstrap.py::archive_codec` | Strict bytes tag and explicit new record/enum registrations; legacy wire preservation |
| `adapters/postgres_archive.py` | Extract existing append body into an internal shared-transaction helper, preserving old behavior |
| `adapters/postgres_planned_execution_archive.py` | Additive capability, immutable binding rows, one source/binding transaction and verified reads |
| `application/planned_bom_execution.py` | Reusable prepare/projection helpers with unchanged default behavior |
| `application/archived_planned_execution.py`, `bootstrap.py` | Lazy injected coordinator, policy validation, current/retained projection and source-free reader |
| `interfaces/execute_package.py`, `interfaces/planned_execution_archive.py` | Opt-in archive mode and strict init/show/history/content caller |
| `tests/planned_execution_archive_fixtures.py`, focused suites | Actual runner-derived core fixtures, codec/adapters/coordinator/public acceptance |
| `tools/package_planned_execution_archive_probe.py`, `tools/package_smoke.py` | Clean installed driver-absent and real storage/restart acceptance, retaining old probes |

### Task 1: Frozen completed-prefix contract and port

**Files:** create `platform/execution/archive.py`, `ports/planned_execution_archive.py`, `tests/planned_execution_archive_fixtures.py`, `tests/unit/test_planned_execution_archive.py`; modify `platform/execution/contracts.py` and its existing unit tests only as needed.

**Interfaces:**
- `PrefixExecutionReceipt.computation_payload: bytes` returns canonical encoding of the exact six fields currently used by execution_digest. execution_digest remains SHA256 of these bytes (not digest() of a bytes object, which would encode it again). Keep the digest byte-equivalent; never normalize timestamps.
- `CompletedPrefixSnapshot(execution:PrefixExecutionReceipt,snapshot:DocumentSnapshot)`; classmethod `from_execution(execution:PrefixExecutionReceipt,policy_parameters:tuple[tuple[str,str],...])->CompletedPrefixSnapshot` projects only retained actual outputs. Properties `scope:StateScope`, `execution_digest:str`.
- `same_computation(left:CompletedPrefixSnapshot,right:CompletedPrefixSnapshot)->bool` compares full computation_payload and canonical snapshot, including policy parameters; never only IDs/digests/Python equality.
- `ExecutionArchiveReceipt(sequence:int,execution_digest:str,retained_receipt_digest:str,source_receipt:ArchiveReceipt)`; derived scope/snapshot_id/receipt_id. Sequence is a positive exact int (not bool); digests lowercaseSHA256; receipt_id is `execution-archive-receipt-v1:` plus the strict canonical digest of this frozen record. Source receipt remains its original contract.
- `ArchivedPrefix(completed:CompletedPrefixSnapshot,receipt:ExecutionArchiveReceipt)` intrinsically binds both digests and exact source receipt scope/snapshot/artifact/hash/assertion count/recorded time.
- `ExecutionHistoryPage(scope:StateScope,after_sequence:int,limit:int,receipts:tuple[ExecutionArchiveReceipt,...],has_more:bool,next_after_sequence:int|None)` validates ordered unique same-scope sequences>cursor, length<=limit, limit1..200/cursor>=0 with bool rejected. has_more requires a full nonempty page and next=last sequence; otherwise next=None.
- `PlannedExecutionArchive` Protocol: `check_ready()->None`; `append(completed:CompletedPrefixSnapshot,content:bytes)->ArchivedPrefix`; `load(scope:StateScope,execution_digest:str)->ArchivedPrefix`; `history(scope:StateScope,*,limit:int=100,after_sequence:int=0)->ExecutionHistoryPage`; `content(scope:StateScope,execution_digest:str)->bytes`. Initialization remains adapter mechanics.

- [ ] Write `test_completed_binding_rejects_foreign_snapshot_policy_and_mention_encoding`: actual existing planned runner -> from_execution fixture; substitute snapshot field/order/mention context/offset or mutable policy pair and require ArchiveContractError. Cover empty, duplicate, unknown/zero and unsupported type/sequence/digest/page metadata.
- [ ] Write `test_first_completion_is_the_only_ignored_computation_field`: valid later/alternate-offset completed_at changes receipt_digest but same_computation remains true; changed policy parameters or actual reexecuted context/source/plan produces a different comparison. Preserve existing execution identity/partial-completion tests.

  Oracle for the fixture's valid first/later bindings:
  ```python
  assert same_computation(first, later)
  assert first.execution.receipt_digest != later.execution.receipt_digest
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_planned_execution_archive.py`; expected RED: missing new module/types, not fixture setup failure.
- [ ] Implement the exact frozen interfaces and projection; reuse strict execution immutability/encoded guards while translating new binding-contract failures to ArchiveContractError. Validate all snapshot fields/five events against the execution chain, and canonical tuple-of-text policy parameters. No domain policy lookup in core.
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_planned_execution_archive.py tests/unit/test_package_execution_contracts.py tests/unit/test_archive_boundaries.py`; expected PASS. Fixture acceptance is core-only; public proof belongs to Task5/6.
- [ ] Commit: `feat: define completed planned-prefix archive contracts`.

### Task 2: Portable execution graph with legacy wire proof

**Files:** modify `adapters/semantic_codec.py`, `bootstrap.py::archive_codec`; create `tests/unit/test_planned_execution_archive_codec.py`, `tests/fixtures/planned-execution-archive/legacy-snapshot-v1.json` and its `.sha256`; preserve `tests/unit/test_archive_codec.py`.

**Consumes/produces:** Task1 records and exact PhysicalPlan bytes; existing SemanticCodec `dumps(value)->str` / `loads(raw:str)` / `node_digest(value)->str` remain the API. Add only the bytes-hex scalar and finite new record/enum registrations; preserve graph schema1 and old snapshot encodings.

- [ ] Before editing the codec, verify its source matches baseline8e72f87. Generate the legacy snapshot golden file once using the existing real five-stage BOM fixture and pre-change codec; retain exact canonical wire and SHA256, using synthetic data only. Later tests load this retained snapshot without requiring its original temporary source URI.
- [ ] Write `test_actual_completed_prefix_roundtrips_with_exact_plan_bytes_and_digests`; require equality of canonical full typed binding, plan bytes/hash, execution/receipt digests and snapshot parameters. Write `test_bytes_tag_is_strict_and_bounded` for empty/all-byte values and malformed uppercase/odd/nonhex/wrong-shape/tag/oversize inputs. Add malformed graph/type/plan/stripped-reference/unknown enum cases with recomputed outer hashes.

  ```python
  loaded = codec.loads(codec.dumps(completed))
  assert canonical(loaded) == canonical(completed)
  assert loaded.execution.plan.canonical_json == completed.execution.plan.canonical_json
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_planned_execution_archive_codec.py`; expected RED: existing encoder rejects bytes/new records.
- [ ] Implement strict bytes tagging/decoding within existing16MiB/50,000/depth64 guards; register Task1 records, PhysicalPlan, five output types, PrefixExecutionReceipt, ResolvedReference, StageExecutionEntry, StageId/StageMode/ExecutionStatus explicitly in bootstrap. No dynamic imports or generic object acceptance; decoded invalid persisted constructors become ArchiveIntegrityError.
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/unit/test_archive_codec.py tests/unit/test_planned_execution_archive_codec.py tests/unit/test_planned_execution_archive.py`; expected PASS, including exact golden legacy wire/hash equality and continued rejection of unregistered roots.
- [ ] Commit: `feat: encode retained planned execution graphs portably`.

### Task 3: Atomic Postgres capability and verified scoped reads

**Files:** create `adapters/postgres_planned_execution_archive.py`, `tests/contract/test_postgres_planned_execution_archive.py`; modify `adapters/postgres_archive.py`, `bootstrap.py`; reuse `tests/postgres_fixtures.py::archive_dsn`.

**Interfaces:**
- `PostgresAssertionArchive._append_in_transaction(conn:psycopg.Connection[dict[str,Any]],snapshot:DocumentSnapshot,content:bytes)->ArchiveReceipt` extracts the existing append body/validation/locks and never opens or commits a connection; public append retains its current transaction and behavior.
- `PostgresPlannedExecutionArchive(source:PostgresAssertionArchive,codec:SemanticCodec)` implements the Task1 port plus `initialize()->None`.
- `bootstrap.build_planned_execution_archive(dsn:str)` lazily constructs the concrete adapter and reuses the existing storage-extra error boundary.

- [ ] Provision a task-owned disposable pinned Postgres16 container on an available loopback port; record exact container ID/label and PIL_TEST_POSTGRES_DSN. Never stop shared containers. Use the existing per-test unique schema fixture; storage skips do not qualify this task.
- [ ] Write actual DB tests: first append/restart/load/content; same computation with later completion returns the first retained full receipt; concurrent16 appends converge to one source/binding; rows/claim membership unchanged on retry. Force a computation-key collision in the test only to prove full canonical comparison rejects different policy/snapshot data rather than trusting a digest. Reject bytearray/wrong-hash/truncated content even when its computation key is already present; a retry must not hide invalid bytes.
- [ ] Write `test_source_and_binding_roll_back_together` using a DB trigger that fails the new binding insert after source writes; assert no new source/content/claim/member/binding rows. Write `test_lost_acknowledgement_does_not_imply_rollback` injecting an error only after a committed transaction, then use a fresh connection to load it and retry without duplication.

  ```python
  retained = archive.append(first, content)
  assert canonical(archive.append(later, content)) == canonical(retained)
  assert (
      retained.completed.execution.completed_at.isoformat()
      == first.execution.completed_at.isoformat()
  )
  ```
- [ ] Add missing base/capability/unknown version, cross-scope, payload/hash/plan/claim/membership corruption, content corruption, immutable UPDATE/DELETE/TRUNCATE and history0/1/100/200/201/cursor/fractional/bool tests. Pin exactly-full last page versus a page with an extra row; verify old AssertionArchive.load/history/content on newly written source snapshots.
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_postgres_planned_execution_archive.py`; expected RED: missing adapter/capability, not absent DB opt-in.
- [ ] Extract the old transactional append helper without changing old payloads, IDs or errors. Add `pil_planned_execution_meta` version1 and immutable `pil_planned_executions` with sequence, scope, execution_digest, retained_receipt_digest, snapshot_id, payload and payload_sha256; UNIQUE(scope,execution_digest), FK(scope,snapshot_id) to source batches. Explicit init requires supported existing archive1 and does not touch other capabilities.
- [ ] Implement one connection/transaction with lock order source batches then execution bindings; validate exact bytes type/hash/length before any retry shortcut, and compare existing validated full computation/snapshot and exact bytes before returning the original acknowledgement. New source/helper and binding writes share that transaction. On read verify checksum, root type, row identities/digests, canonical source snapshot/policy parameters and source membership/content; do not trust equality or projected JSON. Reject invalid history input before SQL; read limit+1 scoped sequence IDs, validate returned records, and evidence has_more without inventing totals. Reuse source connection error sanitization.
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_postgres_archive.py tests/contract/test_postgres_planned_execution_archive.py tests/contract/test_document_review_journal.py tests/contract/test_dependency_store.py tests/contract/test_reviewed_dependency_store.py`; expected PASS with the new atomic/capability cases actually executed.
- [ ] Commit: `feat: retain planned prefix and source evidence in one transaction`.

### Task 4: Actual execution coordinator and source-free reader

**Files:** create `application/archived_planned_execution.py`, `tests/contract/test_archived_planned_execution.py`; modify `application/planned_bom_execution.py`, `bootstrap.py`; preserve `tests/contract/test_package_document_executors.py`.

**Interfaces:**
- `PlannedBomExecutionService.prepare(request:ExecutionRequest)->PreparedPrefix` exposes the existing exact preparation; execute delegates prepare then existing run_prefix with unchanged clock semantics.
- `execution_receipt_payload(receipt:PrefixExecutionReceipt)->dict[str,Any]` extracts the current serializer unchanged. Retained records project through `PlannedBomExecution(PrefixExecution(r.output,r))`; no `.run()` call or external file is needed.
- `ArchivedPlannedBomService(executions:PlannedBomExecutionService,content_store:ArtifactContentStore,archive_factory:Callable[[],PlannedExecutionArchive],policy_parameters:tuple[tuple[str,str],...],validate_completed:Callable[[CompletedPrefixSnapshot],None])`; `execute(request:ExecutionRequest)->ArchivedPlannedBomResult`.
- `ArchivedPlannedBomResult(current:PlannedBomExecution,retained:ArchivedPrefix)` validates the same computation; `.as_dict()` preserves current JSON and adds archive_receipt plus first retained_execution_receipt.
- `execution_archive_receipt_payload(receipt:ExecutionArchiveReceipt)->dict[str,Any]` emits receipt_id, sequence, execution_digest, retained_receipt_digest, scope, snapshot_id and source_receipt; the nested source_receipt uses the existing ArchiveReceipt JSON format, including its receipt_id and ISO timestamp.
- `PlannedExecutionArchiveReader(archive:PlannedExecutionArchive,validate_completed:Callable[[CompletedPrefixSnapshot],None])`: `show(scope:StateScope,execution_digest:str)->ArchivedPlannedBomResult`; `history(scope:StateScope,*,limit:int=100,after_sequence:int=0)->ExecutionHistoryPage`; `content(scope:StateScope,execution_digest:str)->bytes`. Validate returned policy/domain evidence on all read paths; bounded history may validate entries sequentially through load, without retaining all source graphs in memory.
- `bootstrap.build_planned_bom_archive_service(*,manifest:bytes,registry:ImplementationRegistry,config:ImplementationConfig,policy:BomNormalizationPolicy,clock:Callable[[],datetime],archive_factory:Callable[[],PlannedExecutionArchive])->ArchivedPlannedBomService` creates one shared MemoryArtifactContent. `build_planned_execution_archive_reader(dsn:str)->PlannedExecutionArchiveReader` injects retained-domain validation.

- [ ] Write tests counting real five adapters once, forbidding all legacy pipeline `.run()` methods, deleting the source after capture and comparing values/evidence to default planned execution. Repeat the same request with a later clock: five more real calls, distinct current receipt, same first retained receipt/sequence. Empty/duplicate/unresolved/zero/negative/fractional and each/dozen/currency parameters keep existing results.
- [ ] Add invalid runtime + forbidden archive factory/source, missing readiness + forbidden capture, tampered parameters/content digest, and failing append with no success projection. Reader tests forbid executors, source open and current planner/config loading; include differing-offset auxiliary context and supported-policy declaration mismatches. All three reader commands validate retained semantics, not just show.

  ```python
  result = service.execute(request)
  assert calls == list(StageId)[:5]
  assert result.current.execution.receipt.execution_digest == result.retained.receipt.execution_digest
  ```
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_archived_planned_execution.py`; expected RED: missing coordinator/reader.
- [ ] Implement prepare -> lazy archive_factory -> check_ready -> run_prefix -> CompletedPrefixSnapshot.from_execution -> injected policy validation -> content_store.get -> atomic append. Do not call existing execute twice or check an archive cache before execution. Lazy storage construction preserves runtime-before-driver admission.
- [ ] Bootstrap validator reuses validate_bom_assertions and validate_bom_policy_declaration, reconstructs policy from retained canonical parameters and verifies its full resolved NORMALIZE content digest; verify supported MAP schema and ASSERT policy references/digests as well. Candidate binding/policy validation failures become sanitized ArchiveContractError; failures of that validation on retained records become ArchiveIntegrityError. Preserve actual runner/source/normalizer failures in their existing categories. No source/current deployment files are used on read. Reuse pure serializer construction and keep durable_run_journal_updated/result_cache_updated=False.
- [ ] Run `UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/contract/test_archived_planned_execution.py tests/contract/test_package_document_executors.py tests/unit/test_package_execution.py tests/unit/test_package_execution_contracts.py`; expected PASS, including unchanged ephemeral projection and source-free metadata/content/history readers.
- [ ] Commit: `feat: compose explicit durable planned execution and recovery`.

### Task 5: Strict real CLI and restart acceptance

**Files:** modify `interfaces/execute_package.py`; create `interfaces/planned_execution_archive.py`, `tests/integration/test_planned_execution_archive_cli.py`; preserve existing execute/archive/review/replay CLI suites.

**Interfaces:** `execute_package ... --archive` is the only new opt-in. The new module implements init/show/history/content exactly as the spec; DSN stays in PIL_ASSERTION_ARCHIVE_DSN. History JSON includes receipts, has_more and next_after_sequence (null when absent). Reuse existing `assertion_archive.export_content(output:Path,content:bytes)->None` for no-overwrite mechanics; leave old caller syntax unchanged.

- [ ] Write actual subprocess tests: compile manifest -> explicit source archive init -> new capability init -> planned execute --archive -> delete source -> fresh-process show/history/content. Assert exact plan bytes/hash,5 events/12 dispositions, current/retained computation/digests, byte-for-byte export, scoped history and old assertion_archive show using the returned source snapshot ID.

  ```python
  assert (
      body["execution_receipt"]["execution_digest"]
      == body["retained_execution_receipt"]["execution_digest"]
  )
  assert shown["retained_execution_receipt"] == body["retained_execution_receipt"]
  assert exported.read_bytes() == original_bytes
  ```
- [ ] Add later-completion/concurrent retry, missing capability/backend, valid unavailable runtime with absent source, bad arguments/Unicode/digest/scope, pagination boundaries, foreign scope, corrupt storage and existing export path. For lost acknowledgement, call the actual public main with its injected archive factory monkeypatched to commit through the real adapter then raise ArchiveUnavailableError; assert exit2/empty stdout and fresh-process recovery of the one committed record. Do not add product fault flags or timing-based server kills. The real missing-driver environment is qualified in Task6. Existing no-archive output remains unchanged.
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/integration/test_planned_execution_archive_cli.py`; expected RED: missing command/flag.
- [ ] Implement new parser with errors raised inside the sanitized JSON boundary; reject malformed scalar types/ranges and bounded scope metadata before storage. The archive opt-in injects `lambda: build_planned_execution_archive(configured_dsn())`, so environment/driver construction happens after runtime preparation. New reader requires no manifest/registry/config/source argument and never initializes during reads.
- [ ] Run `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache uv run pytest -q tests/integration/test_planned_execution_archive_cli.py tests/integration/test_execute_package_cli.py tests/integration/test_assertion_archive_cli.py tests/integration/test_document_review_cli.py tests/integration/test_correction_impact_cli.py tests/integration/test_archived_bom_query_cli.py tests/integration/test_reviewed_bom_query_cli.py`; expected PASS with actual Postgres and fresh subprocess recovery.
- [ ] Commit: `feat: expose opt-in planned execution archive and recovery CLI`.

### Task 6: Clean artifact, evidence and protected delivery

**Files:** create `tools/package_planned_execution_archive_probe.py`, `docs/architecture/planned-execution-archive.md`; modify `tools/package_smoke.py`, README, package-execution/archive docs, handoff and milestone map. Fixtures remain explicit test inputs, never production defaults.

**Interface:** `package_planned_execution_archive_probe.py SOURCE CONTEXT POLICY REGISTRY CONFIG` uses only stdlib and actual installed commands outside checkout, with DSN from the package-smoke test environment. Print a small semantic result suitable for repeat comparison; never import checkout helpers or leak DSN. Use isolated source copies so destructive source-deletion proof does not break existing probes.

- [ ] Write the installed probe first; run it against a clean baseline8e72f87 wheel and confirm RED from the absent archive command/flag. Also capture baseline default-prefix computation identity through the existing installed probe; require the candidate's default-prefix digest to match for exactly the same source URI/bytes/context/policy/registry/config. This pins the public digest contract despite its private refactor. Integrate real optional-storage commit/delete/restart/show/export/old-reader proof, exact and altered-policy runs, current/retained distinction and new capability failure. Base wheels retain ephemeral prefix acceptance and reject archival with a typed missing-storage diagnostic before source access. Preserve every existing package probe.

  ```python
  assert result["planned_execution_archive_smoke"] == "passed"
  assert result["actual_stages"] == 5 and result["logical_stages"] == 12
  assert result["source_deleted"] and result["retry_retains_first"] and result["export_equal"]
  ```
- [ ] Document explicit initialization, first-retention versus current execution, source-free recovery, pagination, bounds/errors, atomicity/ambiguous acknowledgement, optional dependency and all non-goals. Update handoff/map with main versus branch state; retain broad Issues open.
- [ ] Seal source and run `UV_CACHE_DIR=/tmp/pil-uv-cache make check-fast`, `PIL_TEST_POSTGRES_DSN=<task-owned-dsn> UV_CACHE_DIR=/tmp/pil-uv-cache make check`, `... make package-smoke`, and `... uv run --extra workflow python tools/run_challenges.py --verify-known-bad --results /tmp/pil-planned-archive-challenges.json`. Expected: all required suites/unchanged coverage ratchet pass, genuine storage/artifact cases run, all public oracles pass and known-bad mutations are rejected. Do not turn browser/live opt-in skips into acceptance claims.
- [ ] One fresh whole-branch architecture/semantic reviewer uses the exact spec/plan/Review Focus and latest revision. Resolve material findings with observed RED/GREEN and renew invalidated qualification; record all seven scenario families/commands/review in canonical semantic JSON embedded in the PR. Add a challenge only for any discovered shipped semantic defect, not for an unshipped feature gap.
- [ ] Deliver primary M2 PR: Closes #229 only for complete implementation acceptance; Closes #228 only for approved decision/spec/plan artifacts. Part of #13/#35/#36/#37/#12/#75. Required deterministic checks and final edited-body contract must pass; resolve/rebut arriving actionable review threads. Do not merge pending/failing checks or bypass protection.
- [ ] After authorized merge, prove identical tree and actual main CLI commit/delete/fresh-process recovery/export with code/config pinned to merged revision. Close Issue/Project acceptance, refresh durable delivery receipts, run/review separate roadmap advisory and structural Project audit. Verify and remove only task-owned Postgres resources; preserve unrelated worktrees/services. Expected: confirmed main proof and truthful residual boundaries, not deployment/full-package acceptance.

## Self-review and execution handoff

Task1 supplies the exact binding/port consumed by codec and storage. Task3 supplies the atomic
port used by Task4; Task4's prepare/lazy-factory and current/retained projection feed Task5 without
double execution. Task5's installed commands feed Task6; every Review Focus condition has an
explicit owning regression/public oracle. Codec source bytes remain separate from plan bytes,
old source payloads retain their root type, and read validators cover policy content as well as IDs.

Native/inline execution with one independent final review preserves the established workflow.
The six tasks share contracts and transaction/projection boundaries; separate implementer forks
would repeat context without making these dependencies independent. Owner approval of the written
spec authorizes this plan; review this plan before product implementation. No new runtime or
storage capability is delivered by the planning commit.
