# Explicit planned execution through source assertions

Status: proposed for maintainer review, not approved or implemented.
Decision Issue: [#225](https://github.com/stauntonjr/procurement-intelligence-lab/issues/225).
Primary M9; parent #12; part of #7/#20/#35/#75. Baseline: main `07d089b` / PR #224.

## Purpose and current gap

Resume the reusable core architecture after the document/archive/correction slices. Success is
one real source-to-assertion run selected by the existing package planner, with actual typed
stage outputs and execution evidence. No new demo, business policy, model or queue is needed.

The manifest declares twelve logical stages. `plan_manifest` validates all deployment selections
and emits a deterministic physical plan; it does not load executors. Existing BOM services run
five real stages through direct nested composition. `bootstrap.build_application` is still a
placeholder. An advertised descriptor is neither a registered executor nor execution evidence.

The intended outcome is grounded in the user's core-architecture direction. Selecting the
five-stage boundary, leaving later stages unvisited, and initially rejecting neutral execution
are proposals in this document, not decisions inferred from an existing implementation.

## Alternatives and recommendation

1. **Explicit synchronous prefix through ASSERT (recommended).** Connect planning to the five
   existing implementations and retain all later declarations as not executed. This tests real
   runtime selection and evidence before adapting resolver/reconciler authority policies.
2. **Execute the full procurement plan.** This includes RESOLVE/RECONCILE/DERIVE/DETECT and requires
   additional policy/input admission and acceptance. It is too broad for the next slice.
3. **Keep direct composition and add more producers.** Useful application behavior, but it leaves
   the accepted planner/runtime boundary unexercised. Preserve current callers for compatibility.

Do not change downstream EXECUTE bindings into EMPTY merely to report a complete package run.

## Authoritative inputs and preflight

Inputs are the exact compiler-admitted manifest, immutable implementation descriptor registry,
explicit deployment configuration, explicit `stop_after=ASSERT`, one scoped SourceReference,
caller-pinned execution context, injected server clock/content store, and explicit normalization
policy. Policies and schema references resolve through composition-owned typed records; no
ambient business defaults, arbitrary imports, executable callbacks in authoring data or secrets
in the manifest. Documents never select executors or grant authority.

Build the full plan through the unchanged `plan_manifest` path. All current full-plan compatibility
requirements still apply, including metadata selections beyond ASSERT. Preserve the plan bytes
and hash; a public caller cannot substitute a hand-constructed PhysicalPlan. Derive runtime
selections from that newly validated plan, not a second independent stage order or ID list.

Deployment injects a separate immutable runtime registry associating exact selected descriptors
with stage-aware executor objects. In-boundary descriptor identity, implementation version,
contract versions, declared configuration schema/settings and resolved policy/schema references
must match the selected plan and concrete registration before any source/content I/O or stage
call. Duplicate, absent, wrong-stage or mismatched registrations fail closed. Required policy
parameters are validated before execution and their full canonical digest binds the run.

Beyond-boundary descriptors remain compatibility advertisements only; those executors need not
be registered or available. Their existence cannot establish health or executed semantics.
Fixtures used to demonstrate a full plan must label later advertisements as planning-only;
do not ship fake later executors as operational defaults. An attempt to execute beyond the
supported boundary fails preflight, rather than silently shortening a requested run.

Initially support only five contiguous EXECUTE stages, INGEST through ASSERT. Reject EMPTY or
PASSTHROUGH inside this boundary before I/O. Stage-specific neutral materialization/validation
needs its own acceptance slice. Neutral declarations outside the boundary remain unvisited.

## Ownership, invocation and typed wiring

Platform owns immutable runtime registration/execution contracts and the fixed logical order.
Use stdlib dataclasses and Protocols. No platform or port imports procurement or dispatches on
domain/profile names. Composition resolves domain schema/policy and concrete local-file, XLSX,
BOM-map, normalization and assertion strategies. Domain algorithms remain under procurement.

Invoke each selected stage exactly once using the actual preceding output. Do not implement a
stage adapter by rerunning the complete legacy nested pipeline or by merely registering its
already-created result. Keep SourceReference, Artifact, StructuredDocument, MappedDocument,
NormalizedObservation, SourceAssertion and EntityMention contracts, including typed auxiliary
AssertionOrigin/batch/event inputs. A common untyped `dict[str, object]` is not a new semantic API.

The first caller accepts one source and requires INGEST to produce exactly one matching artifact;
zero/multiple artifacts reject. STRUCTURE retains that artifact and MAP that document and selected
schema. NORMALIZE retains mapped fields, exact policy, units, diagnostics and immutable batch
evidence. ASSERT consumes those actual observations and origin; every observation is represented
exactly once and valid mentions stay linked to their source assertions. Zero observations may
produce an evidenced empty assertion batch; missing/invalid values remain explicit unresolved
observations and claims. Duplicate source rows and conflicting claims are not collapsed.

Adapt or share existing pure validators, transformation builders and serializers so this runtime
cannot bypass guards already enforced by DocumentStages/NormalizedDocumentStages/
AssertedDocumentStages. New transport records must represent stage-specific multiplicity and
auxiliary evidence explicitly, not infer it from the singular catalog contract name. Output
shape, source identity, scope, full encoded provenance and policy/schema bindings are checked
after every invocation; a plausible-looking output is insufficient.

## Execution evidence and completion

Return actual source/intermediate/assertion evidence plus a separate immutable execution receipt
with all twelve ordered logical entries. It binds manifest hash, plan hash, runtime-config hash,
resolved policy/config digests, full registered implementation identities, code/run/context,
source content and actual input/output/event references. Local metadata remains caller-pinned,
not production attestation. Secret values and raw backend details are not receipt fields.

The first five entries are SUCCEEDED only after actual invocation and contract validation.
The other seven are NOT_EXECUTED with reason `outside_requested_prefix`, preserving each original
mode and declaration. This applies even to PREDICT/DECIDE/ACT EMPTY declarations: no stage-specific
empty output was produced. Do not assign invented output references, success times or quantities
to unvisited stages. Return `requested_prefix_complete: true`, `package_execution_complete: false`,
and `stop_after: ASSERT` only on positively evidenced prefix success.

Keep computation identity separate from server completion time. Equivalent explicit inputs and
pinned execution context yield equal computation/result identities; recording a fresh attempt
does not promise identical receipt time or exactly-once processing. Retain exact timestamp
encoding and full context metadata in the relevant digests, not only datetime equality. Source
observed/captured/execution times must be timezone-aware and consistent with the injected clock;
record completion after the final validated stage. Propagate exact scope through all outputs.

This receipt is returned to the caller; no archive schema, durable run journal, new result cache,
ingestion request-deduplication guarantee, automatic correction replay or global completeness
claim is introduced. Existing archive/review/replay commands keep their separate durable contracts.

## Public caller and failure behavior

Add a separate trusted-local CLI, tentatively `interfaces.execute_package`, with explicit source,
manifest/registry/config files, `--stop-after ASSERT`, context and normalization policy. Compose
the runtime at bootstrap. Keep existing planner/BOM/archive/review/replay callers unchanged;
do not turn the placeholder `build_application` into a hidden default/service locator.

The CLI strictly reads bounded UTF-8 JSON/TOML, rejects duplicate keys, unknown fields, malformed
Unicode and unsupported time/version/identity/container types, and emits sanitized typed JSON
failures/exit2 without partial success stdout. Plan admission retains PlanningError. Runtime
admission versus invoked-stage contract failure versus infrastructure unavailability must be
distinguishable; specific codes and owning records will be fixed in the implementation plan,
before coding. Never relabel unavailable or failed execution as EMPTY or successful prefix work.

Fail fast on a stage error, invoking no later executor. Retain already captured evidence within
the attempt, but publish no success receipt or durable registration. No database/queue/action is
in this caller; rollback of arbitrary external side effects is not claimed. RequestContext is
required when a future public/remote boundary grants authority. This local file-processing caller
does not inherit REVIEW/action permissions from other services or provide production authentication.

## Acceptance and scenario dispositions

| Family | Required implementation evidence |
|---|---|
| Empty/missing/unknown | Empty source bytes/unsupported document fails typed; missing executor/policy/context fails before I/O; actual zero-row document retains evidenced empty batches; null/invalid mapped values preserve unresolved diagnostics |
| One/many/duplicate/conflict | One source, multiple fields/rows; zero/multiple captured artifacts reject; duplicate source rows/conflicting claims survive; malformed duplicate runtime registrations/selections reject |
| Scope/time/as-of | Foreign source/scope/lineage or altered context/time encoding rejects; future/malformed clock/context fails; full plan and policy identity retained; no governed as-of winner selection |
| Numeric/boundary | Existing zero/negative/fractional quantity/price semantics unchanged; source multiplicity and strict file/type bounds tested; no silent truncation or sentinel zero |
| Unsupported/malformed | Missing/mismatched selected executor/version/config/policy, changed manifest/plan and unsupported neutral/beyond-boundary request reject; unavailable is distinct from a successful empty result |
| Public/artifact | Real new CLI invokes five registered actual implementations once, retains five transformation chains and all twelve dispositions; clean wheel outside checkout repeats it; non-procurement executable fixture uses the identical runner |
| Safe counterexample | Current full planner bytes/contracts and all legacy BOM/archive/review/replay outputs remain compatible; semantic values/locations/statuses/units match the legacy five-stage caller under equivalent policy; different workflow/plan identity may intentionally give new provenance IDs |

Negative public tests must show no executor/source I/O on preflight failure, no later invocation
after a failing stage, no success stdout and no fabricated downstream events. Metamorphic tests
cover registry-order invariance and changed selected implementation/policy/config identity.
No model/algorithm swap is proposed; fixture conformance is engineering evidence, not extraction
quality or a second production vertical. Add a development-agent challenge only for a shipped
semantic defect actually found during implementation; do not invent a historical failure.

## Delivery and review boundary

This proposed spec and [ADR-043](../../adr/043-explicit-planned-prefix-execution.md) need maintainer
ratification before an implementation plan. Issue #225 tracks that decision, not delivered code.
After approval, scope a feature Issue and plan covering typed contracts, runtime admission,
actual five-stage adapters, public/installed acceptance, independent semantic/architecture review,
exact-head full coverage/ratchet/challenges and normal protected PR delivery. One inline implementer
and a fresh final reviewer are recommended; shared contracts make parallel implementers wasteful.

Read Issues #12/#20/#21/#31/#32/#33/#35/#36/#75/#149/#151/#205 and ADR006/017/019/022/037/042 before
implementation. No broad milestone or parent Issue closes from the prefix alone. Queue/control
plane, durable job attempts, neutral execution, full nine-stage execution, canonical/governing
policies, prediction/action authority, model swaps and deployment remain separate decisions.
