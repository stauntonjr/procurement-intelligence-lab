# Durable local RESOLVE jobs

Status: proposed for owner review. The owner selected this runtime direction after PR243; this
written proposal is not yet approved and provides no runtime acceptance. Primary M1,
[Issue #244](https://github.com/stauntonjr/procurement-intelligence-lab/issues/244), native parent #36.
Baseline: main `7426724078af1038ad8b009b8cccf236e31dec82`. Proposed ADR048 records the boundary.

## Intent and constraints

Give the already-qualified six-stage RESOLVE path the durable, explicit local job lifecycle of
ADR045. A developer must be able to submit pinned inputs, deliberately start/retry/abandon an
attempt, distinguish uncertain acknowledgement from failure, and recover exact evidence after
removing the original files. Catalog availability or a changed deployment must not rewrite history.

Preserve ADR045/046 and the fixed platform topology. Core owns identity/transition/evidence
semantics; Postgres owns transaction mechanics; bootstrap wires implementations. Use frozen
stdlib dataclasses and ports/Protocols, with no domain imports in platform or ports. Only the
existing deterministic `procurement_item` / `internal_sku`, `bom-normalized-exact@1` algorithm is
admitted. There is no new matching, authority, freshness, aggregation or arithmetic policy.

The existing five-stage records, graph tags, hashes, command IDs, JSON projections, rejection
behavior, initialization and callers remain compatible. No implicit migration or widening of v1.
There is no listener, queue, worker, lease, automatic retry, partial-stage continuation, general
multi-profile engine, RECONCILE job, fresh seven-stage orchestration or external side effect.
Developer actor labels remain provenance, not production authentication or operational-agent rights.

## Approaches and selected engineering proposal

1. **Add an explicit sibling six-stage job profile.** Recommended: it preserves the frozen
   five-stage format while reusing the real resolved executor and archive. It costs new typed
   journal bindings, explicit capability initialization and compatibility tests.
2. Widen existing five-stage jobs in place. Rejected by ADR046: it changes pinned v1 validation,
   serialized graphs, supported recipes and success evidence.
3. Chain a successful five-stage job to an independent resolver job. Rejected for this slice:
   it cannot establish one atomic six-stage job success and changes retry/publication semantics.

The owner selected durable RESOLVE jobs as the direction; option1 and the detailed choices below
are the author's proposed implementation, subject to approval of this document.

## Inputs and identities

Introduce `PinnedResolvedPrefixDefinition` containing:

- the full existing `PinnedPrefixDefinition` for the admitted first-five execution (manifest,
  registry, config, exact source/context/capture request, normalization parameters, plan and
  first-five resolved reference/schema/policy metadata);
- the exact `CandidateInputEvidence`, including raw UTF-8 catalog bytes and their SHA256;
- the exact `ResolutionPolicyEvidence` and sixth registration metadata (descriptor/settings,
  resolved references and policy version; no executor object or callable);
- recipe `procurement.bom-local-resolved-prefix@1`, and explicit RESOLVE stopping semantics.

Admission reconstructs `PreparedResolvedPrefix` from these pins and compares the complete typed
pinned definition. All config selection settings (including later unvisited stages) and context
environment must be empty, as in the secret-free original job profile. Code revision must match
application version. Current executors are checked before a new claim; there is no provider,
recipe, policy or schema fallback. Submission validates all inputs before constructing storage
and never opens source bytes. The resolved policy and catalog use the existing strict parsers.

`ResolvedJobDefinition` retains the existing `ArtifactArrival`, scoped idempotency key and pinned
resolved definition. New identity prefixes are:

- job: `local-resolved-prefix-job-v1:` + SHA256 of canonical `(scope, idempotency_key)`;
- attempt: `local-resolved-prefix-attempt-v1:` + SHA256 of `(scope, job_id, ordinal)`;
- transition: `local-resolved-prefix-transition-v1:` + SHA256 of the typed transition.

Request digest covers the entire canonical typed job, including raw catalog audit bytes. Same
scope/key with equal full request returns the original submission acknowledgement; changed raw
bytes, semantic catalog, policy, arrival or runtime pins conflict. Reordered catalog keys or JSON
whitespace can keep the existing semantic computation identity while changing request/receipt
identity: raw-byte changes are not an exact submission replay. Different keys are distinct jobs,
even when they compute the same execution digest.

Arrival event uniqueness is `(new profile, exact scope, event_id)`. ASSERT-only and RESOLVE job
journals are independent namespaces; there is no new cross-profile/global arrival registry.
Within the new namespace, equal arrival replays and changed arrival conflicts, even across job
keys. This choice adds no restrictions to existing five-stage submissions.

Exact four-part source scope is tenant/project/site/version. Source observation, capture,
context start and catalog effective time retain the ADR046 rules; source observation must not
exceed capture or announcement, catalog effective time must not exceed capture, and source,
capture/context start/announcement must not be later than server admission as applicable.
Lifecycle times are aware fixed-offset datetimes and cannot regress. No age-derived freshness or
new time-based authority rule is inferred.

## Lifecycle and reusable boundary

Reuse existing `ArtifactArrival`, status/intent/kind enums, finite `JobFailure` diagnostics,
canonical identity/bounds primitives and the ADR045 transition policy. Add distinct resolved
request/command/token/success/transition/receipt/view/history dataclasses because existing
constructors deliberately validate exact five-stage types and prefixes. Their names and codec
tags are distinct; new records cannot be decoded as an old job.

Keep the old lifecycle and public projection unchanged. Small behavior-preserving internal helper
extraction is allowed where needed, but a generic workflow engine or broad old-record refactor is
out of scope. Parametrized policy-contract tests must show both profiles obey the same lifecycle,
clock, version and fence rules; frozen wire/digest fixtures independently protect old behavior.

| Current state | Explicit operation | Outcome |
|---|---|---|
| SUBMITTED | newly acknowledged FIRST | RUNNING with first ordinal/fence |
| RUNNING | active-token atomic publication | SUCCEEDED |
| RUNNING | acknowledged pre-publication failure | FAILED |
| RUNNING | exact active-attempt abandonment | ABANDONED; old publication right fenced |
| FAILED / ABANDONED | newly acknowledged RETRY | RUNNING with next ordinal/fence |
| SUCCEEDED | new run/retry/abandon | conflict |

Versions/sequences begin at1 and advance together; ordinals/fences are positive signed64-bit
values. After abandonment the subsequent retry advances its publication fence beyond the
abandoned token. START keys are shared by FIRST/RETRY within one job; ABANDON has its existing
separate command family. Exact key/payload replay returns original acknowledgement metadata,
not a newly current command. Changed intent, actor, expected version or payload conflicts.

Historical START lookup happens before current source/config/executor preparation. Replayed
success is validated retained evidence; replayed failure/abandonment reports the historical
outcome even if a later attempt succeeded. Unresolved RUNNING stays busy/uncertain; no elapsed
time proves death. An unacknowledged claim grants no execution right. Abandonment is deliberate
fencing, not process cancellation or rollback.

## Six actual stages and complete result binding

A newly acknowledged attempt invokes `run_resolved_prefix` and its existing first-five runner
once. Add an optional capture-guard injection through the resolved runner, passed immediately to
`run_prefix`; the default remains unchanged for old six-stage callers. Actual INGEST hash/length
must match the declared arrival before STRUCTURE or any subsequent executor runs. Do not emulate
this with a second pre-read/capture, a fabricated receipt or an executor wrapper that changes
semantic implementation identity.

Preserve pinned context/run/capture/catalog/policy values across retries, while attempt/server
lifecycle identity remains separate. Completion must bind exact source, plan, effective prefix
context, normalization parameters, all five stage metadata/reference sets, sixth selected
implementation/policy/decision provenance, semantic catalog AND raw catalog evidence, six-stage
receipt/output, and actual raw source bytes to the frozen request. A changed receipt, catalog,
policy, raw source or attempt cannot become a same-attempt completion replay.

An attempt retains its full `CompletedResolvedPrefixSnapshot`. Success carries its separate
`ResolvedExecutionArchiveReceipt`; the embedded prefix and source archive links remain explicit.
The existing resolved computation equivalence controls first-retention sharing. A prior prefix
or resolved computation can have a different first-retained completion timestamp or catalog raw
representation, without replacing this attempt's exact full evidence. Never substitute a first
retained receipt for the actual current attempt receipt.

Every execution retains all twelve stage dispositions: the first six succeeded; RECONCILE through
ACT are NOT_EXECUTED. Requested-prefix processing can complete while package completion is false.
An empty document still has six actual stage events. Unknown quantity is not zero. No match,
collisions, punctuation-only mentions and null/blank SKU rows keep the existing abstention/unlinked
behavior and original numeric claims; none is a failed job solely because identity abstained.

## Postgres capability and transaction

Add explicit `local_resolved_prefix_jobs/v1` with independent immutable arrival/job/transition/
command tables and a validated CAS head in `pil_local_resolved_prefix_job_*`. It requires explicit
source-archive1, planned_prefix_archive/v1 and planned_resolution_prefix/v1 capabilities. It does
not require or initialize the old local_prefix_jobs/v1 capability. Reads never initialize schema.
Bounded allowlisted codec registration adds the distinct new record tags without altering old
serialized values. No pickle, dynamic imports or callbacks are persisted.

Extract the existing resolved archive append body into a transaction-scoped internal helper;
its current `append` continues to open/check one transaction and delegate with identical semantics.
The new journal's `complete` owns one connection/transaction and uses the helper. Required order:

1. Lock and validate the requested resolved-job head and newest immutable transition.
2. Bind the complete supplied result/raw bytes to the pinned request and validate exact active
   token/fence, or validate byte-for-byte full same-attempt completion replay.
3. Retain source bytes/snapshot/claims and first-five execution using existing archive mechanics.
4. Retain resolved execution/catalog/evidence using existing resolved-archive mechanics.
5. Append the full actual-attempt success transition and update the CAS head, then commit.

Use the same archive lock order as current writers after acquiring the job head. No lock spans
executor I/O. A stale success/failure writer must be fenced before any new source/result write.
Concurrent success and abandonment serialize; the loser conflicts. Failure at any publication
checkpoint leaves no partial new source/prefix/resolved/job success. Preexisting retained records
survive rollback. Source-free successful reads verify current attempt, first resolved archive,
first independently retained prefix and source checksum/links, not just the head status.

## Failure and acknowledgement contract

Add resolved-job error codes with input invalid/not-found, policy conflict/busy/fenced and
infrastructure integrity-invalid/unavailable categories; preserve existing codes on old callers.
Reuse the finite allowlisted failure diagnostics. Do not retain raw exception, driver, source,
DSN or credential text. Admission/input failures and failed storage readiness do not invent a
submitted job or attempt. Acknowledged pre-publication execution failure may append FAILED.

The publication call is outside the execution-failure catch. Lost completion acknowledgement may
mean committed SUCCEEDED or unresolved RUNNING; do not append FAILED or infer rollback. Failure
journal outage likewise cannot establish FAILED. Exact reads/replay are the recovery path.
Unavailable public responses retain validated scope/job ID and acknowledged attempt ID when
known; lost START acknowledgement cannot fabricate an attempt ID.

## Public caller and recovery

New explicit module: `python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs`.
Commands: `init`, `submit`, `run`, `retry`, `abandon`, `show`, `history`, `result`, `content`.
Old processing_jobs arguments/output stay unchanged and do not silently select a new profile.

Submission uses existing source/arrival/context/manifest/registry/config/normalization-policy/
idempotency-key inputs, plus required `--resolution-policy`, `--candidate-snapshot`, and explicit
`--stop-after RESOLVE`. Other commands use only exact `--scope`, `--job-id` and the existing
explicit command fields; `content` has an explicit non-overwriting atomic `--output`.

`show` reports journal status, frozen arrival/request/candidate identities and positive completion
only when SUCCEEDED. `history` is ascending per-job sequence, default100/max200, exclusive
nonnegative cursor, real limit+1 `has_more`; it claims no frozen global view or total.
`result`/`content` require positively validated success. No source/catalog/config/current executor
is needed for retained reads or exact successful START replay. Cross-profile IDs reject rather
than falling through to another journal. Wrong-scope lookups do not disclose another scope.

Output keeps these roles explicit (no result cache or exactly-once physical-invocation claim):

- `job_journal_receipt`, original `command_receipt`, per-call `historical`/`observed_version`;
- `attempt_execution_receipt` (current six), `attempt_prefix_execution_receipt` (its embedded five);
- `retained_execution_receipt` (first six), `retained_embedded_prefix_execution_receipt` (its five),
  `retained_prefix_execution_receipt` (first independently retained five), and `archive_receipt`;
- original claims, resolution outcomes/abstentions/canonical links/unlinked assertion IDs and exact
  current catalog audit bytes; retained roles are never relabeled as a new invocation.

Abandon output retains original historical command receipt plus current observation, so late
replay cannot claim it abandoned a later attempt. Strip legacy cache/journal booleans from new
execution projections without changing those legacy projections. Success/metadata uses exit0;
failures use exit2, sanitized JSON stderr and empty success stdout.

Bounds retain the original local profile: key1..256 characters; other identity/actor/reason text
1..4096; fixed-offset aware times; strict lowercase SHA256; exact nonnegative bytes/cursors;
metadata1MiB/context-arrival-policy-catalog32KiB; allowlist graph16MiB/50,000 nodes/depth64; history
limit1..200. Existing catalog bound0..256 unique nonblank raw keys of1..256 characters is unchanged.
Oversize/duplicate fields/unsupported values fail, never truncate or select defaults.

## Acceptance and delivery gates

The implementation plan is produced after this proposal is approved. Preserve Native/inline
execution with one independent final whole-branch reviewer. Gates, in order:

1. Contract/identity/codec/lifecycle and parametrized shared-policy tests, including exact old
   IDs/wire/graphs/rejections. Instantiate invalid records directly, not only via CLI validation.
2. Pinned admission, six actual executor counters and arrival mismatch before STRUCTURE; explicit
   failure/retry/historical replay without source or current executor construction.
3. Real Postgres atomicity/races/first-retention differences, stale writers, success-abandon races,
   no acknowledgement inference, corrupt links and an internally consistent stale head.
4. Real public subprocess submit/run/retry/abandon/show/history/result/content, malformed/cross-scope
   and source/config/catalog deletion, process death/restart, atomic export/no-overwrite behavior.
5. Clean base/storage wheels outside the checkout on Python3.12/3.13; base missing-storage errors
   are typed, installed storage exercises the real Postgres path. Compare old public payloads,
   IDs, graph bytes, semantic outputs and unchanged archive/job schemas on frozen fixtures.
6. `make check`, package smoke and affected challenge verification; latest-revision semantic
   evidence and one final independent review. Synthetic cases qualify integration only, not
   held-out identity quality. New defect oracles/challenges apply to shipped defects actually fixed.
7. Required protected PR checks, main tree equality and installed main proof; then close only #244,
   synchronize handoff/map/Project and clean only owned resources. #36 and broader M3 stay open.

Scenario coverage must include empty/one/many, exact duplicate keys/raw catalog collisions,
unknown/missing SKU/quantity, changed audit bytes, cross-scope, stale/future/time boundaries,
zero/negative/fractional values with unchanged domain behavior, malformed/oversize/unsupported
inputs, concurrent/replayed commands, failed/abandoned/succeeded historical outcomes, prior
independent archive records and pre/post-publication faults.

## Decisions left to the builder

Module splitting, SQL helper placement, private test fixture organization and fault-injection
mechanics may follow repository conventions. They cannot widen old contracts, weaken binding,
change the transition/namespace/public-output rules above or introduce operational authority.
Material contract changes return for owner review rather than being inferred from implementation.
