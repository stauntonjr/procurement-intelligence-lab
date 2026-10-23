# Durable local prefix jobs and fenced attempts

Status: proposed for owner review, decision [#231](https://github.com/stauntonjr/procurement-intelligence-lab/issues/231),
primary M1, native parent #36. Owner instructed proceed with the recommended job/attempt/idempotency
design after PR230. This document proposes lifecycle policy; no product implementation is authorized
by the proposal alone. Baseline main `87cc5ccb967e2063b348f90744aaafae741e66b1`.
Proposed [ADR-045](../../adr/045-local-prefix-jobs-and-fenced-attempts.md).

## Intent and current evidence

A developer should be able to submit a pinned local source-processing request, deliberately execute
or retry it, and inspect what happened after a process restart. A repeated delivery/request must not
silently create another job, run another attempt, duplicate claims, or assert success without
retention evidence. A lost acknowledgement must remain distinguishable from a failed computation.
This is core processing infrastructure for #36, not another demo journey.

Main executes the actual INGEST → STRUCTURE → MAP → NORMALIZE → ASSERT prefix through explicit
runtime admission (ADR043), and atomically archives its source evidence and completed receipt
(ADR044). Archive identity is `(exact scope, execution_digest)`. Only completion time may differ
on an equal computation retry; the first committed full receipt remains retained. Every call of
the existing archived execution service still executes five stages. It has no durable submission,
active-attempt, failure or abandonment record. No current job/queue/attempt promise follows from it.

Authoritative contracts: Issues #36, #13/#21/#33/#35/#37, ADR017/019/022/038/043/044 and the
[execution](../../architecture/package-execution.md) and
[archive](../../architecture/planned-execution-archive.md) contracts. #41 correction authority,
#68 operational-tool approvals/retries and #70 agent-run audit remain separate; this design does
not repurpose their approval states, SQLite records or operational permissions. #75 retains
broader control-plane/runbook work. None of these broad Issues closes with the first local slice.

## Approaches and recommendation

The owner selected continuation through #36's local synchronous contract rather than wider stage
adoption. These storage/lifecycle choices within that direction are the author's proposal:

| Approach | Benefit | Cost / disposition |
|---|---|---|
| Frozen contracts and an in-memory coordinator | Smallest initial surface | No durable failure or unresolved-attempt evidence after restart; inadequate for this proposed acceptance |
| Durable local journal around the qualified prefix | Explicit submission, attempts, fencing and restart reads; reuses Postgres/source retention | New lifecycle policy and additive transaction boundary; recommended for written approval |
| Listener/queue, leases, distributed workers and automatic retries | Event-driven production direction | Adds scheduling, expiry and external-side-effect authority not established by #36's local foundation; deferred |

Build on stdlib frozen dataclasses/Protocols, the current codec, optional Postgres and explicit
bootstrap composition. No new runtime dependency, provider, model, algorithm or generic workflow
framework. No cloud/queue choice. Table/column names and private helper organization are left to
the implementation planner, subject to the atomicity, immutability and lock-order rules below.

## Semantic contract

- **Inputs:** a caller-declared artifact-arrival record, scoped idempotency key, complete pinned
  prefix definition, explicit start/retry/abandon commands and exact bytes actually captured.
- **Output:** an immutable job definition, append-only attempt/lifecycle evidence, a validated
  current-state projection and, only after successful atomic completion, the current attempt's
  full receipt plus its existing first-retained archive binding.
- **Scope/time:** exact tenant/project/site/version on every operation. Preserve fixed-offset
  timestamp encoding; source observation ≤ pinned capture/context start ≤ submission's server
  time. Arrival announcement must not be in the future at admission. Server lifecycle times
  cannot regress along a job's transitions. A server time behind a previous retained transition
  fails typed rather than normalizing it. Pinned capture/start is semantic context, not each
  attempt's wall-clock start or proof of independent production capture.
- **Policy:** exact-key/full-canonical request admission, one active fenced attempt, explicit
  first attempt/retry/abandonment, unchanged first-computation retention, no automatic retry.
- **Evidence:** arrival declaration, full pinned inputs/plan/resolved metadata, lifecycle command
  identity/actor/time/reason, attempt ordinal and fence, typed failures, current receipt and
  first retained receipt, original source/claim/mention/event evidence and bytes.
- **Failures:** closed typed job contract/conflict/busy/fenced/not-found/integrity/unavailable
  failures plus existing classified execution failures. Never turn unknown into failed, empty,
  zero, success, rollback or permission. Never expose DSNs, raw driver errors or arbitrary logs.

All new contracts use exact immutable types and full canonical comparisons, not Python datetime
or nested-object equality alone. Reuse the existing bounded canonical/graph profiles:16MiB,
50,000 nodes/depth64, strict lowercase SHA256/bytes-hex and finite record/enum registrations.

## Arrival and pinned request

An `ArtifactArrival` is a declaration, not proof that bytes exist: exact scope, caller event ID,
SourceReference, expected lowercase SHA256, expected nonnegative integer byte length, and aware
announcement time. Empty bytes are a legitimate expectation; invalid XLSX remains a later typed
interpretation failure, not an empty document. `event_id` and idempotency/command keys are exact
valid UTF-8 text,1..256 characters, no surrounding whitespace. All other retained identity text
uses the existing bounded execution profile. Reject bool/fractional/negative lengths and ordinal/
version/cursor values; integer storage counters must fit positive signed64-bit where applicable.

The same scoped event ID may be referenced by several jobs (for example distinct policies).
Repeated event ID with different canonical arrival content conflicts, even if a digest happens to
collide. A changed source revision, expected hash/length, observation or encoded offset is a
changed arrival. No identity is inferred from a URI, mtime, basename or source-version label.

A `PinnedPrefixDefinition` contains the exact manifest bytes, typed registry/config, original
ExecutionRequest, canonical normalization parameters, full PhysicalPlan and the resolved
per-stage references/policy/schema metadata admitted from PreparedPrefix. It retains enough
neutral metadata to derive the exact effective execution context currently produced by
PreparedPrefix.context. Do not compare that derived context directly to the caller's original
config_digest: admission derives it from the pinned request, plan and selected metadata.
The definition's canonical payload, not merely a set of hashes or config paths, is authoritative.

Submission uses the existing full planner/runtime/policy admission before journal construction
or source I/O. Require one ASSERT-stopped prefix with the five qualified local deterministic
adapters; later declarations remain planning metadata/NOT_EXECUTED. Reject unsupported settings,
versions and recipes before submission writes. To make restart execution portable without storing
secret-bearing deployment values, this first job profile requires **empty settings for every
config selection, including later unvisited stages**. Store no callable, credential or environment
secret. Registry/config/policy can be reconstructed from retained typed data; unknown runtime
recipes are not resolved by input-driven imports.

The composition root supplies a stable explicit local-prefix recipe and procurement policy
validation. Neutral platform records/ports do not import procurement, psycopg or framework types.
A read can validate pinned data/plan consistency without source or executor I/O; execution
additionally checks that the current deployment actually supports the exact retained recipe and
versions. No silent fallback, upgrade or replan. A changed code/config/policy/context needs a new
request/key, not mutation of an admitted job.

## Job and command identity

`submit(scope, idempotency_key, arrival, definition)` atomically admits the arrival and immutable
job with an initial SUBMITTED record. Scope must agree throughout. The job ID is a namespaced
full canonical digest of `(scope, idempotency_key)`; its independent request digest covers the
complete arrival/definition. Compare complete canonical values on every retry and on reads.
Submission server recording time is excluded from equality; preserve the first submission receipt.
The journal validates capability readiness before writes. Submission does not open/capture the
source, execute any stage or claim that the declared bytes were verified.

An exact repeated submission returns the same job and receipt. Same key with any changed pinned
content conflicts. Different keys create distinct jobs, even when their computations later share
an archive binding; there is no global semantic/hash deduplication policy. Likewise, a job is not
an execution_digest: that digest cannot be known positively until actual outputs exist.

A mutation command includes kind, scoped job ID, explicit command key, caller-declared developer
actor, expected job version and relevant attempt/reason data. Actor labels are provenance, not
production authentication. Namespace command uniqueness by job and command family: START (FIRST and RETRY share it)
or ABANDON. FIRST/RETRY intent remains part of the payload, so reusing an old start key
with changed intent conflicts. Compare the
entire immutable command on replay; changed actor/intent/version/attempt/reason with the same key
conflicts. An exact replay returns the original command acknowledgement without reapplying its
transition, even if the current job later advanced. Responses label that receipt historical and
also identify the current observed version; never pretend an old abandonment affected a new attempt.

Initial job version is1. Every acknowledged transition increases it by1. Positive exact64-bit
versions/attempt ordinals are validated intrinsically. Start requests always require a supplied
key and expected version; do not generate a fresh key behind repeated CLI invocations.

## Attempt lifecycle and retry

Job status is the projection of acknowledged lifecycle evidence:

| Current state | Explicit command / observed result | Next state and evidence |
|---|---|---|
| SUBMITTED | `run` / FIRST with matching version | RUNNING; new STARTED attempt/fence |
| FAILED or ABANDONED | `retry` / RETRY with new command key and matching version | RUNNING; next attempt ordinal/fence |
| RUNNING | Actual complete prefix plus atomic archive/success commit | SUCCEEDED; current receipt and retained binding |
| RUNNING | Observed typed failure before completion publication begins, acknowledged failure append | FAILED; sanitized classified failure |
| RUNNING | Explicit `abandon` naming active attempt/version/reason | ABANDONED; invalidate that attempt's publication fence |
| SUCCEEDED | Any new run/retry/abandon command | Conflict; original success remains immutable |

Attempts are STARTED, SUCCEEDED, FAILED or ABANDONED; they are not new domain claims. There is
at most one STARTED attempt per job. Start serializes on the job head and returns an explicit
`newly_claimed` disposition. Only the invocation receiving a newly acknowledged claim may execute.
Identical concurrent start commands converge to that claim; every replay receives `newly_claimed:
false` and must not execute. This per-call claim disposition is outside the immutable STARTED
receipt; replay retains that receipt unchanged while withholding execution permission.
A different start key against an active or terminal job does not
launch another attempt. No source I/O is allowed before start acknowledgement.

A repeated run/retry command whose attempt already succeeded returns its retained result and
historical command receipt without execution. If its attempt is still STARTED, return a typed
busy/unresolved response. If it failed or was abandoned, report that recorded outcome; a new
attempt needs an explicit new RETRY command, never a repeated old start request. Metadata `show`
may successfully return RUNNING/FAILED/ABANDONED without claiming processing success. Actual
execution command failures use exit2/JSON stderr/empty success stdout; acknowledged metadata or
submission reads use exit0 and explicit status/completion fields.

Manual retry is permitted after FAILED or ABANDONED regardless of recorded failure category;
it is an operator-requested rerun of unchanged immutable inputs, not an inference that the fault
is transient or fixed. There is no automatic retry, backoff or timeout expiry. Deterministic bad
inputs may fail again; changing them requires a new request. Existing operational-tool retry
policy under #68 is neither widened nor reused. No arbitrary global retry-count policy is added;
counter overflow fails typed and bounded history does not truncate retained attempts.

Keep the **same original execution request and effective semantic context across attempts**.
Do not inject attempt ID/server start into run_id, capture time, input_snapshot_ids or config_digest:
that would manufacture new assertion/provenance identities on an identical processing retry.
Attempt ID, ordinal, server start/end and command actor/time are separate durable journal evidence.
Real successful retries still execute all five stages; their computation is equal and original
archive/claim identities converge. Current completion may differ and is retained per attempt.
The proposal does not guarantee single physical invocation or globally exactly-once processing.

## Source verification and actual execution

Execution of a newly claimed attempt loads only the retained request/config/policy and admits
its exact recipe before claiming. It then invokes the real registered five-stage runner.
An application-supplied capture guard verifies the actual CapturedOutput content hash/length
against the arrival **immediately after INGEST and before STRUCTURE**; the underlying capture
still supplies the actual artifact, bytes and provenance. This guard does not invoke capture
twice, replace the captured object or fabricate an event/implementation. Retain the declared
expectation in the job and the verified actual artifact in successful output evidence.

A source that changed at the same URI must fail this check before later stages or archive writes.
The run uses the captured content store, so later URI mutation/deletion cannot change that attempt's
input. A restored source with exactly the declared bytes may be used by an explicit retry.
Retry from only previously archived bytes is not silently substituted for local capture in this
first profile. Read/recovery commands never reopen the source. Failed attempts do not claim durable
intermediate outputs that were never committed; stage-progress persistence remains broader #36 work.

## Atomic completion, failures and ambiguous acknowledgement

Successful publication must be one transaction: validate current active attempt/fence and pinned
request/output binding, retain original source bytes/snapshot/claim membership and existing
completed-prefix binding, append the full **current attempt** PrefixExecutionReceipt with its
archive acknowledgement, and advance the job head to SUCCEEDED. Verify exact source, scope,
plan, effective context, resolved metadata, policy parameters and output chain; compare the
capture against the expected bytes again at persistence. Never accept only a supplied digest.

First-retained execution remains unchanged under ADR044; the attempt success record stores its
own full current receipt (including completion encoding) and the first retained archive receipt.
These may have different receipt digests while sharing a computation. A retry's failure cannot
rewrite the first retained receipt or original claims. The completion operation is idempotent
only for the **same exact current-attempt receipt and bytes**; a different completion for the
same attempt is a conflict even if the underlying archive would retain the first computation.

The port exposes atomic completion rather than calling separate archive.append and journal.finish
APIs. Postgres may extract a transaction-sharing helper from the planned-prefix adapter, as that
adapter already shares the source helper. Preserve every old caller/format/ID. Initial lock order
is job admission/head first, then source batches, then execution bindings; no old archive path
acquires a job lock and no new command reverses this order. Never hold these locks over executor I/O.

If execution/candidate validation fails **before calling completion publication**, append a FAILED
record with the original stable failure code/category and an allowlisted public diagnostic, not
str(exc), raw exception/driver text, source contents or arbitrary metadata. Persist known semantic
failure families separately from unavailability of the journal. Unknown programming failures receive
a sanitized internal/infrastructure diagnostic; never invent a successful result. Failed-append
acknowledgement loss leaves publication uncertain, not positively acknowledged FAILED.

After completion publication starts, **any unavailable/ambiguous acknowledgement leaves the caller
uncertain**. Do not catch it and append FAILED: the success may already have committed. Return a
safe typed unavailable response with scoped job/attempt IDs, no rollback claim or success stdout.
Fresh lookup finds either acknowledged SUCCEEDED with all bound evidence or still RUNNING; atomicity
forbids a committed new source/result without the corresponding terminal attempt/job transition.
Existing evidence from an unrelated/earlier computation can exist without implying this attempt
succeeded. Start/submission/abandon acknowledgement loss similarly requires exact-key lookup/replay;
no executor starts after an unacknowledged claim.

## Explicit abandonment and fencing

RUNNING after a crash means unresolved, not failed or expired. No heartbeat timeout proves the
old process stopped. `abandon` requires exact scope/job/active attempt, expected version, command
key, actor and bounded nonempty reason. It records the operator's decision to invalidate that
attempt's publication right, not proof that execution never ran or a hard cancellation occurred.

Successful abandonment advances the fence and makes the old attempt terminal ABANDONED. A later
retry may claim the next attempt. An old worker racing publication must recheck its fence inside
the same transaction **before any source/result write**. If abandonment won, publication fails
fenced and leaves no new archive evidence. If success won, abandonment conflicts without changing
success. Old failure publication must also fail fenced and cannot alter a newer attempt's state.

These guarantees apply to the qualified local file/read-and-memory prefix and its transactional
retention. They do not undo capture I/O, stop computation, cancel external side effects or make
arbitrary future executors safe. An implementation must not admit side-effecting extensions or
later stages under this job profile without a separate contract and acceptance.

## Storage, readers and public boundary

Propose explicit additive `local_prefix_jobs/v1` initialization on supported source archive1 plus
planned_prefix_archive/v1. No implicit migrations, capability initialization during reads, or
alteration of review/dependency/approved-correction records. Port-level policy stays independent
of DB mechanics. Immutable job/arrival/command/attempt evidence is append-oriented; a small mutable
job-head projection serializes CAS/fence decisions and must agree with immutable transition evidence.
This is not generic application-wide event sourcing or a claim of database-owner adversarial safety.

Retained job payloads/current receipts use the bounded allowlisted codec. Explicitly register
neutral planning-input/metadata and journal records; no pickle, callbacks or dynamic imports.
Validate stored checksum/root/IDs/canonical bindings, scope, versions, command identity, head-to-
transition relationship and referenced source/archive evidence. Corrupt/missing linked records are
integrity failures, not empty history or absence of a job. Validate the evidence actually returned;
a bounded page is not a claim that all undisplayed historical records were inspected.

A new trusted developer module, provisionally `interfaces.processing_jobs`, has explicit `init`,
`submit`, `run`, `retry`, `abandon`, `show`, `history`, `result` and `content` commands. DSN remains
only in PIL_ASSERTION_ARCHIVE_DSN. Submit takes an arrival/request document and explicit current
manifest/registry/config/context/policy files; execution/retry takes scoped job identity, command
key, actor and expected version, reconstructing **stored** inputs. Abandon additionally names
attempt and reason. Reads require exact scope/job and no source/config/executor argument.
`result`/`content` require positively recorded success and validate bound current/retained evidence;
`show` reports truthful current state without implying execution completion.

History is scoped per job, ordered by durable sequence with exclusive nonnegative cursor,
default100/max200 and actual limit+1 evidence for has_more/next_after_sequence. No invented total,
implicit latest-winner claim or frozen view across pages. A reused command receipt is visibly
historical; metadata can additionally show the current job version without rewriting its receipt.
Export reuses atomic non-overwriting mechanics. JSON/Unicode/digest/bounds and parse errors remain
sanitized with empty success stdout/exit2 on failure. Existing metadata file bounds1MiB/32KiB,
codec bounds and bounded text apply; no DSN/path/settings/secret echo in failure diagnostics.

Existing execute_package and planned_execution_archive commands and receipt digests/JSON remain
unchanged, including the old caller's journal/cache flags. New job output has separate
`job_journal_receipt`, `attempt_execution_receipt` and `retained_execution_receipt` fields.
Its execution receipt projection retains exact underlying receipt data/digests but does not copy
the old caller's workflow-side-effect booleans. Acknowledged job-journal mutation is asserted only
by its own validated receipt. No result cache, operational agent tool or new REVIEW/ACT authority.

## Required acceptance evidence

| Scenario family | Positive evidence and required counterexample |
|---|---|
| Empty/missing/unknown | Actual zero-row prefix succeeds with five events/twelve entries; null/unresolved stays distinct from zero; absent source/capability/current result fails typed; RUNNING after restart stays unresolved |
| Multiplicity/conflict | Duplicate/conflicting source rows survive; exact submission/start/terminal replay retains first acknowledgements; changed same-key payload conflicts; concurrent same/different start keys yield one active publication right |
| Scope/time | Cross-scope job/command/result/content not-found; exact offset/context/policy binding; pinned semantic times unchanged across attempts, server times nonregressing; future arrivals/admission and stale expected versions fail |
| Numeric/bounds | Empty bytes versus empty document; zero/negative/fractional quantities and each/dozen/currency unchanged; counters/limits reject bool/fractional/negative/overflow; graph and input limits reject, not truncate |
| Unsupported/malformed | Unknown recipes/versions/settings/policy and malformed codec/metadata rejected before side effects; missing driver/capability before capture; head/command/current-vs-retained/source corruption fails integrity |
| Public/artifact | Actual compiled-plan submit→run→restart→show/result/export in real Postgres; delete source and all original config inputs before reads; base missing-driver diagnostic; installed optional wheel; every legacy caller remains compatible |
| Safe counterexample | Kill/restart after submission/start and after actual committed success before acknowledgement; injected mid-completion failure rolls back new source/result/terminal writes; abandon-versus-complete/failure race fences old writers; forbid source/executor I/O on reads and every replayed start |

Also qualify distinct current receipts across explicit identical-input retries with one original
claim/snapshot/computation binding; mismatched bytes at a reused URI rejected immediately after
capture; abandon then retry then old-worker publish rejected; terminal success cannot be retried;
late replay of an old abandonment returns only its old receipt; failure-journal outage and success
acknowledgement ambiguity do not invent terminal outcomes. Required tests use actual runner/CLI/
installed package boundaries and isolated real Postgres, not helper-only acceptance. Persisted
attempt records must include actual full current receipt, not an unrecoverable hash-only pointer.

Require latest-revision semantic evidence, full checks/coverage ratchet, clean package, all public/
known-bad challenges and independent semantic/architecture review. A discovered shipped defect
gets its own regression/challenge; an unshipped feature gap is not a shipped-defect claim.
A new implementation Issue/plan will own this bounded acceptance after written-design approval;
#36 remains open for broader listeners/workers/partial-stage persistence/production processing.

## Boundaries, builder calls and delivery

No automatic retry/replan/recompute, queue/listener/lease scheduler, hard cancellation, latest source
selection, governing/canonical state, approval bypass, new resolution/model policy, production auth,
backup/HA/deployment/throughput guarantee, neutral or later-stage execution. Original assertions and
existing public behaviors remain authoritative. No confidential/proprietary material.

Author calls proposed for approval: durable local journal; expected-byte arrival declarations;
fully pinned secret-free input recipe; immutable semantic context across attempts; explicit manual
retry after failure/abandonment; fenced abandonment; one source/archive/current-attempt success
transaction; historical command replay; source/config-free reads. Table/index/helper naming and
fixture organization are routine builder choices, not new lifecycle policy.

Fresh builder check precedes owner handoff. This document and ADR045 remain proposed until owner
approval. Under the brainstorming skill, implementation planning follows approval of this written
design; no product code, storage capability, CLI or runtime acceptance is delivered by these docs.

Pre-slice stewardship: existing hosted audit39715621577 on the identical main baseline failed
Gemini503; a current direct Codex review of canonical docs/Issues/Project is separate. No successful
hosted report/provider repair is claimed. Confirmed residual drift: duplicate ADR033 and old active
demo wording in #68/#70/#75; these do not authorize demo work. The stale pending-plan Test Layers
fields on completed228/229 were reconciled to their actual PR230 delivery evidence.
