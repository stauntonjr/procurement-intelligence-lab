# Planned source-assertion prefix implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the five existing BOM stages selected by a validated package plan and return honest twelve-stage execution evidence.

**Architecture:** Keep the existing full planner unchanged. A separate injected runtime registry admits the exact five selected executors before source I/O; a synchronous domain-neutral runner validates typed transitions and records later declarations as NOT_EXECUTED. Composition supplies real strategies and explicit domain policy.

**Tech Stack:** Python3.12+, frozen stdlib dataclasses, Protocols, existing planner/semantic contracts, pytest/ruff/pyright; no new runtime dependency or database schema.

**Spec:** [approved written design](../specs/2026-10-21-planned-prefix-execution-design.md); policy #225/ADR043; implementation #226, primary M9/parent #12. Baseline main `07d089b`; proposed design revision `150b5b9`.

## Global Constraints

- Initially support only five contiguous EXECUTE stages, INGEST through ASSERT. Reject EMPTY or PASSTHROUGH inside this boundary before I/O.
- Build the full plan through the unchanged `plan_manifest` path. Preserve the plan bytes and hash; no supplied PhysicalPlan is accepted as admission proof.
- The other seven are NOT_EXECUTED with reason `outside_requested_prefix`, preserving each original mode and declaration, including later EMPTY declarations.
- Return `requested_prefix_complete: true`, `package_execution_complete: false`, and `stop_after: ASSERT` only on positively evidenced prefix success.
- Platform never imports procurement or branches on domain/profile names. No callbacks in declarative authoring data, implicit business defaults, fake executor fallback or secret values in receipts.
- One actual source; INGEST returns exactly one matching artifact. Preserve every mapped field/observation/claim, original evidence, duplicates/conflicts and null/unresolved; positive evidence supports empty batches.
- New caller only. Keep current manifest/planning schemas, existing caller outputs/IDs and archive/review/replay wire shapes unchanged. New workflow/plan provenance intentionally gives new execution identities.
- Receipt is ephemeral: no run journal, result cache, exactly-once claim, general replay, canonical/governing-state policy, action authority, browser or deployment acceptance.

## Review Focus

1. A complete valid plan with a missing selected in-prefix executor must fail before source I/O; unregistered executors beyond ASSERT must remain NOT_EXECUTED.
2. Same-instant/different-offset timestamps or substituted context/policy content must not alias encoded execution identity or satisfy exact returned-output validation.
3. A stage can return a valid-looking foreign source/field/origin/event; validate actual transition lineage and stop before invoking the next stage.
4. Empty observations are evidenced batches, while absent/invalid inputs are errors or unresolved claims; duplicate source tokens must retain separate source rows.
5. Later EMPTY declarations must never acquire fake success/output IDs, and changing their plan metadata must still change the bound plan identity.

## File and interface map

Source paths below are relative to `src/procurement_intelligence_lab/`; tests/tools/docs paths are repository-relative.

New `platform/execution/outputs.py` owns five frozen payloads and stage-specific transport; `contracts.py` owns request/invocation/receipt identities; `executors.py` owns the Protocol and immutable registrations. `admission.py` validates the full plan and runtime selection; `runner.py` invokes the fixed prefix. These modules depend only on shared semantics/planning contracts.

New `platform/semantics/document_lineage.py` extracts existing pure guard logic. Existing application document/normalization/assertion services call the same guards, retaining their result builders and serialized outputs. New `adapters/package_document_executors.py` delegates the existing injected strategies, one call per stage. New `application/planned_bom_execution.py` converts typed outputs to existing public result payloads plus the execution receipt. `bootstrap.py` owns real procurement composition. New `interfaces/execute_package.py` owns file loading/argv/error JSON. No plan or registry file is imported as Python code.

### Task 1: Typed outputs, shared lineage guards and execution identities

**Files:** create `platform/execution/{__init__,outputs,contracts}.py`, `platform/semantics/document_lineage.py`, `tests/unit/test_package_execution_contracts.py`; modify `platform/semantics/errors.py` and the three existing `application/*document_stages.py` files.

**Interfaces:**
- Frozen `CapturedOutput(artifact:Artifact,event:TransformationEvent)`, `StructuredOutput(previous:CapturedOutput,document:StructuredDocument,event)`, `MappedOutput(previous:StructuredOutput,document:MappedDocument,event)`, `NormalizedOutput(previous:MappedOutput,observations:tuple[NormalizedObservation,...],provenance:DecisionProvenance,policy_reference:str)`, `AssertedOutput(previous:NormalizedOutput,assertions:tuple[SourceAssertion,...],mentions:tuple[EntityMention,...],origin:AssertionOrigin,provenance:DecisionProvenance)`. Normalized/asserted outputs compute `batch_id` and `event` with existing batch identities and exact legacy event semantics; do not accept caller-supplied batch IDs.
- `StageInput = SourceReference | CapturedOutput | StructuredOutput | MappedOutput | NormalizedOutput`; `StageOutput` is the five output variants. No object/dict payload bag. Every record exposes computed `stage`, `reference_ids` and event evidence appropriate to its concrete type.
- `ExecutionRequest(source:SourceReference,context:ProvenanceContext,captured_at:datetime,stop_after:StageId)`; `ResolvedReference(declaration_ref:str,reference_id:str,content_digest:str)`; `StageInvocation(stage:StageId,provenance:DecisionProvenance,captured_at:datetime,references:tuple[ResolvedReference,...])`.
- `StageExecutionEntry(stage:StageId,mode:StageMode,status:ExecutionStatus,reason:str|None,implementation_id:str|None,input_ids:tuple[str,...],output_ids:tuple[str,...],event_id:str|None)` uses a closed `ExecutionStatus` enum SUCCEEDED/NOT_EXECUTED. NOT_EXECUTED has only reason `outside_requested_prefix` and no event/input/output/implementation-execution evidence; the declaration/selected metadata remains in the retained plan.
- `PrefixExecutionReceipt(plan:PhysicalPlan,context:ProvenanceContext,source:SourceReference,references:tuple[ResolvedReference,...],output:AssertedOutput,entries:tuple[StageExecutionEntry,...],completed_at:datetime)` validates twelve unique ordered entries, exactly five real successes, consistent scope/context/clock and bound actual event/output references. Its computed completion properties are requested_prefix_complete=True/package_execution_complete=False only for that valid evidence chain. `execution_digest` excludes server completion time; `receipt_digest` includes it. Canonical digests encode full dataclasses/enums/timestamps with ISO offset, sorted keys and strict UTF-8, not datetime equality or only provenance_id.
- Add `PackageExecutionError`/`pil.input.package_execution_invalid`, `PackageExecutionContractError`/`pil.interpretation.package_execution_contract_invalid`. Existing infrastructure exceptions retain their own codes/categories; do not turn driver/provider text into public messages.

- [ ] Write RED `test_package_execution_contracts.py`: malformed containers/enums/Unicode/time, wrong stage/payload, contradictory receipt entries, substituted event/source, duplicate fields/claims/mentions, unsupported boundary, empty batch and full timestamp/context digest identity. Assert seven later EMPTY/EXECUTE entries cannot claim events or success.

  Core oracle, using typed output/receipt fixtures defined in this test file:
  ```python
  assert receipt.requested_prefix_complete is True
  assert receipt.package_execution_complete is False
  assert tuple(e.stage for e in receipt.entries) == tuple(StageId)
  assert all(e.event_id is None and e.output_ids == () for e in receipt.entries[5:])
  ```
- [ ] Run `uv run pytest -q tests/unit/test_package_execution_contracts.py`; expect missing execution contracts, not fixture/setup failure.
- [ ] Implement exact immutable records and extract `validate_capture`, `validate_structure`, `validate_mapping`, `validate_normalization`, `validate_assertions` from existing guards, with exact platform types/provenance arguments and existing DocumentStageError behavior. Preserve domain assertion-validator injection. Use the same helpers in output records and old services; exact encoded-context comparison supplements intrinsic source/event checks for the new runtime.
- [ ] Run new contracts plus `tests/unit/test_document_stages.py`, `tests/unit/test_normalized_document_stages.py`, `tests/contract/test_bom_normalization.py`, `tests/contract/test_bom_assertions.py`. Existing source/evidence/value/identity oracles must remain unchanged.
- [ ] Commit the typed contracts/shared guards and passing verification.

### Task 2: Exact runtime admission and domain-neutral synchronous runner

**Files:** create `platform/execution/{executors,admission,runner}.py`, `tests/unit/test_package_execution.py`, `tests/execution_fixtures.py`.

**Interfaces:** consumes Task1 payloads/request/receipt. `StageExecutor.invoke(inputs:StageInput,*,invocation:StageInvocation)->StageOutput` is a Protocol. `ExecutorRegistration(descriptor:ImplementationDescriptor,settings:tuple[tuple[str,str],...],references:tuple[ResolvedReference,...],executor:StageExecutor)` and `ExecutorRegistry(registrations:tuple[ExecutorRegistration,...])` are frozen; duplicate IDs reject.

`prepare_prefix(manifest:bytes,*,registry:ImplementationRegistry,config:ImplementationConfig,executors:ExecutorRegistry,request:ExecutionRequest,now:datetime)->PreparedPrefix` calls the unchanged full planner and returns the admitted plan/request/five registrations. Frozen `PreparedPrefix(manifest,registry,config,executors,request,plan)` retains the exact typed originals and revalidates full planning output/hash and in-boundary registration admission in `__post_init__`; no public constructor accepting only a plan is used. `run_prefix(prepared:PreparedPrefix,*,clock:Callable[[],datetime])->PrefixExecution` returns `output:AssertedOutput` and `receipt:PrefixExecutionReceipt`. Revalidate prepared input/hash/registration invariants intrinsically; a manually forged PhysicalPlan or swapped request cannot bypass admission.

Runtime configuration settings for each selected stage equal the registration's exact canonical settings. Resolved references cover the binding's domain_config_ref and policy_refs exactly; use declaration_ref for exact binding coverage, reference_id for the concrete resolved instance and content_digest for its full canonical content. Declaration labels and parameter-instance identities are distinct; compare all three to composition-resolved records. Schema/policy content digests change computation identity even when a policy label is unchanged. No ambient read inside platform.

- [ ] Write RED tests with counting/no-I/O executors: `test_preflight_missing_executor_before_io`, `test_exact_descriptor_settings_and_references`, `test_rejects_neutral_or_wider_prefix`, `test_outside_executors_not_required`, `test_substituted_output_stops_chain`, `test_unvisited_empty_is_not_success`, `test_registry_order_invariance`, `test_full_encoded_identity`, and `test_non_procurement_same_runner`.

  Counterexample oracle: remove the selected ASSERT registration from an otherwise valid full-plan fixture, then `prepare_prefix` must raise PackageExecutionError with every counting executor at0 and no source/content-store read. A STRUCTURE lineage failure permits INGEST/STRUCTURE counts1 but leaves MAP/NORMALIZE/ASSERT at0 and returns no PrefixExecution.
- [ ] Run `uv run pytest -q tests/unit/test_package_execution.py`; expect missing admission/runner.
- [ ] Implement exact preflight before any invoke: stop_after must be StageId.ASSERT, first five plan modes EXECUTE, selected descriptors/versions/contracts/config/settings/refs exact, portable context with application_version==context.code_revision, aware fixed-offset observed_at<=captured_at==context.started_at<=now. Keep all twelve plan declarations. Clock must be valid before execution and after final validated output, and completion cannot precede start.
- [ ] Invoke each registered executor once in catalog order over actual prior output; construct deterministic component provenance from the selected descriptor, resolved policy/schema and full effective configuration digest. Validate exact input/source/scope/encoded provenance/output/event bindings after each invoke. Stop on first typed failure; never publish a partial success receipt. New infrastructure failures are sanitized at their adapter boundary.
- [ ] Run new unit suite plus `tests/unit/test_package_planning.py`; verify full planning bytes and unavailable-selection failures remain unchanged. Commit.

### Task 3: Real five-stage adapters and explicit procurement composition

**Files:** create `adapters/package_document_executors.py`, `application/planned_bom_execution.py`, `tests/contract/test_package_document_executors.py`; modify `bootstrap.py`. Use existing capture/structure/map/normalize/assert strategies, content-store port and domain validators.

**Interfaces:** five concrete executors implement Task2's Protocol, consuming Task1's precise previous output and StageInvocation. They receive their existing strategy instances through constructors; ASSERT receives `Callable[[AssertionOrigin],AssertStrategy]` and the existing typed batch-validator callback. `build_planned_bom_service(*,manifest:bytes,registry:ImplementationRegistry,config:ImplementationConfig,policy:BomNormalizationPolicy,clock:Callable[[],datetime],content_store:ArtifactContentStore|None=None)->PlannedBomExecutionService`; service `execute(request:ExecutionRequest)->PlannedBomExecution`. Its `.as_dict()` combines the existing AssertedDocumentResult payload with `execution_receipt`; no invented downstream semantic outputs.

Composition registers fixed actual IDs `local-file-capture`, `xlsx-cell-structure`, `bom-table-map`, `bom-value-normalization`, `bom-source-assertions`, each implementation_version `1`. Use current catalog contracts and capability metadata (`tables` for STRUCTURE); reject aliases/versions that do not match these adapters. No fake later executors. Existing full-registry fixtures may advertise later stages strictly as planning-only.

- [ ] Write RED real strategy contract tests: five invocation counts exactly1; source mutated/deleted after capture still uses retained bytes; empty workbook rows, duplicate tokens, unknown/invalid fields, quantity0/negative/fractional and each/dozen policies retain legacy semantics. Compare source values/coordinates/units/statuses to legacy five-stage run, allowing new plan/workflow provenance IDs only.
- [ ] Add no-I/O cases for unsupported schema/policy ref, wrong config setting/version and selected implementation; test returned foreign field/observation/origin/claim/mention and equal-instant substituted provenance against shared guards. Run the contract file to observe missing adapters/composition failures.
- [ ] Delegate one existing strategy call per executor; construct actual typed outputs/events through shared builders/guards. For existing serializers reconstruct DocumentStageResult -> NormalizedDocumentResult -> AssertedDocumentResult from retained outputs without invoking legacy `.run()` methods. Keep default `build_application()` behavior unchanged.
- [ ] Resolve actual schema/fixed assertion policy and normalization parameters at composition. NORMALIZE resolves manifest declaration `procurement.normalize/bom-decimal@1` to policy.reference_id plus canonical full dataclass digest. ASSERT resolves `procurement.assert/bom-claims@1` to fixed instance `bom-assertions@1`; preserve the current domain component schema/policy labels. Schema resolution retains the current BOM_TABLE_SCHEMA reference. Declaration/instance IDs remain distinct and all enter the receipt; selected declaration labels must match the unchanged manifest. Each registration's expected settings equal the explicit config selection; selected settings are configuration identity, not permission to override typed policy. Reject unsupported non-empty settings for the initial adapters; policy/schema material stays in explicit resolved references.
- [ ] Run adapter contracts plus existing BOM stage/normalization/assertion contracts and unit suites. Commit only with original callers still green.

### Task 4: Strict real CLI and public boundary acceptance

**Files:** create `interfaces/execute_package.py`, `tests/integration/test_execute_package_cli.py`, `tests/fixtures/execution/{procurement-registry.json,procurement-config.toml}`; modify `tests/execution_fixtures.py` for non-procurement executable data.

**Interface:** `python -m procurement_intelligence_lab.interfaces.execute_package SOURCE --manifest MANIFEST.json --registry REGISTRY.json --config CONFIG.toml --stop-after ASSERT --context CONTEXT.json --normalization-policy POLICY.json`. Source is local; context uses the existing explicit scope/observed_at/captured_at/source_version/run_id/code_revision shape. New workflow identity `planned-source-assertion-prefix`, version `1`; request start=captured_at. Runtime builder creates full effective config/context digest from plan/config/policy, preserving caller pinning labels.

- [ ] Write RED actual subprocess tests: real compile manifest -> new CLI -> five transformations and twelve receipt entries; seven NOT_EXECUTED entries have no output/event references; source values match legacy CLI; missing executor/neutral/wider boundary/malformed JSON/unknown options fail JSON exit2 with empty stdout. Use an intentionally nonexistent source to prove admission errors win before file I/O.
- [ ] Run `uv run pytest -q tests/integration/test_execute_package_cli.py`; expect missing command, not malformed test setup.
- [ ] Implement read limits: manifest/registry/config1MiB each, context/policy32KiB each; UTF-8/duplicate keys/non-finite JSON/unknown fields and invalid Unicode reject. Use `load_registry(bytes)`, `load_config(bytes)` and unchanged planner validation; strict bounded context/policy loading belongs in the new CLI, without widening legacy parsers. Argparse error override emits the same typed JSON/exit2; help may remain ordinary stdout. No source-file I/O before service preflight.
- [ ] Emit only one complete JSON document/newline after validated success; preserve existing semantic exceptions, add PlanningError issues without settings values, sanitize unexpected infrastructure detail at its actual boundary. No environment DSN/reviewer or operational-agent permission is used.
- [ ] Run new integration plus legacy planner/BOM/archive/reviewed CLI suites and the non-procurement runner oracle. Commit.

### Task 5: Clean artifact, evidence and protected delivery

**Files:** create `tools/package_execution_probe.py`, `docs/architecture/package-execution.md`; modify `tools/package_smoke.py`, README, runtime-planning doc, handoff and milestone map. Keep deployment fixture files in tests; package smoke passes them explicitly, never as production defaults.

- [ ] Add failing clean-wheel acceptance invoking the new CLI outside the checkout using real installed adapters. Check explicit full plan/hash, actual five outputs/events, all twelve dispositions, unknown/duplicate row preservation, typed unavailable executor and equality of computation IDs across install directories with identical source/context inputs. No helper-constructed execution record substitutes for this path.
- [ ] Integrate one complete real path into existing base/storage wheel smoke, preserving all prior probes. Reuse a source URI when comparing IDs across environments; if source URI differs, compare semantic payload and verify each bound source identity rather than requiring false full-receipt equality. No new optional dependency or fake later runtime resource.
- [ ] Document exact CLI/config/policy/receipt/failure contract and explicitly distinguish original planning-only metadata, prefix completion, full execution, ephemeral attempt receipts and archive durability. Update handoff/map with merged-versus-planned language; preserve #12/#7/#20/#35/#36/#75 and other broader Issue boundaries.
- [ ] Seal source; run focused suites, `make check`/coverage ratchet, `make package-smoke` with dedicated disposable Postgres, and all30 public oracles/known-bad mutations. Add a challenge/regression only if a shipped semantic defect is found. Record exact commands/head and seven-family dispositions in canonical semantic evidence JSON embedded in PR.
- [ ] Apply architecture-review/review-semantic-change with one fresh whole-branch reviewer; resolve material findings RED/GREEN and renew invalidated qualification. Keep unresolved/pending evidence not_ready. All required deterministic PR checks and final body-bound contract must pass; resolve/rebut actionable automated threads before merge.
- [ ] Deliver normal PR: primary M9; Closes #226 only for full feature acceptance, Closes #225 only for approved decision/spec/plan artifacts merged; Part of broader work. After authorized merge verify same tree on main, actual new CLI pinned to merged revision, Issue/Project closeout/audit and separate advisory roadmap result. Remove only task-owned resources; no production or browser claim.

## Plan self-review and execution handoff

All five Review Focus classes map to explicit Task1/2/3 tests. Task2 consumes Task1's finite
payload/receipt contracts; Task3 supplies Task2's exact registries and actual outputs; Task4
uses Task3 composition; Task5 qualifies Task4's installed caller. Existing full planner and
legacy wire identities remain unchanged. Policy/config admission, zero/unknown semantics,
non-procurement reuse and public/package proof are explicit, not delegated to generic helpers.

Recommended method: native/inline with one independent final review, preserving the previous
delivery method. Shared payload/admission/adapter contracts make per-task implementer forks
unhelpful. The written spec is approved; this newly written plan is presented for maintainer
review before Task1 under the writing-plans execution-handoff rule. No runtime code has changed.
