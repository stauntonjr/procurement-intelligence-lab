# Durable local prefix jobs

Decision #231 / accepted [ADR-045](../adr/045-local-prefix-jobs-and-fenced-attempts.md),
implementation #232, primary M1, part of #36. The [approved design](../superpowers/specs/2026-10-23-local-prefix-jobs-design.md)
and [plan](../superpowers/plans/2026-10-23-local-prefix-jobs.md) define the bounded acceptance.
This branch implements the local synchronous profile; main/delivery qualification is recorded in
#232 and the handoff. It adds no distributed queue, production deployment or operational-agent authority.

## Inputs and admission

Submit a source, explicit arrival declaration, manifest, registry, config, context, normalization
policy and idempotency key. All selection settings, including unvisited later stages, and the
pinned context environment must be empty in this first secret-free local profile. The exact
supported recipe is `procurement.bom-local-prefix@1`; bootstrap resolves its five deterministic
adapters. Unknown recipes/settings/versions/policies are rejected rather than upgraded or replanned.

An arrival JSON document has exactly these fields (use the actual expected hash/length):

```json
{"event_id":"delivery-1","expected_content_hash":"<lowercase SHA256>","expected_byte_length":1234,"announced_at":"2026-10-23T12:00:00+00:00"}
```

The existing execution context supplies the exact four-field scope, source observation, pinned
capture time, run ID, source version and code revision. The source reference is declared from its
path without opening it. Arrival is an expectation, not evidence that bytes exist. Observation
must not exceed capture/context start; those times and announcement must not exceed server admission.
Submission admits runtime and policy before constructing storage, retains the full pinned typed
definition and declaration atomically, and does no source capture. Same scope/key plus full canonical
payload returns the original acknowledgement; changed content conflicts. The scoped event ID also
cannot be reused for a changed arrival. Different job keys remain distinct even for equal computations.

## Explicit capability and commands

Set `PIL_ASSERTION_ARCHIVE_DSN` only in the environment; install the optional `storage` extra.
Initialize source archive1, then planned_prefix_archive/v1, then local_prefix_jobs/v1 explicitly.
Reads never initialize or migrate schemas. Existing archive/review/dependency tables and old
commands, JSON, identifiers and digests retain their contracts.

```bash
python -m procurement_intelligence_lab.interfaces.assertion_archive init
python -m procurement_intelligence_lab.interfaces.planned_execution_archive init
python -m procurement_intelligence_lab.interfaces.processing_jobs init
python -m procurement_intelligence_lab.interfaces.processing_jobs submit source.xlsx \
  --arrival arrival.json --context context.json --manifest manifest.json \
  --registry registry.json --config config.toml --normalization-policy policy.json \
  --idempotency-key delivery-request-1
python -m procurement_intelligence_lab.interfaces.processing_jobs run \
  --scope scope.json --job-id JOB_ID --command-key first --actor developer --expected-version 1
```

`submit` returns scoped job identity and SUBMITTED evidence, never processing success. `run` needs
an explicit FIRST command; `retry` needs an explicit new RETRY key and exact current version after
FAILED or ABANDONED. FIRST/RETRY share the START key namespace: reusing a key with changed intent,
actor/version/payload conflicts. One newly acknowledged claim executes. Exact replay has no new
invocation right and performs no source/current-executor preparation. An unacknowledged claim
never authorizes execution. A replay of a failed or abandoned attempt reports that recorded outcome;
it does not launch a retry even when another attempt later succeeded.

| State | Allowed next event | Result |
|---|---|---|
| SUBMITTED | FIRST | RUNNING with one active attempt/fence |
| RUNNING | actual atomic completion | SUCCEEDED |
| RUNNING | acknowledged pre-publication failure | FAILED |
| RUNNING | explicit exact-attempt abandonment | ABANDONED |
| FAILED / ABANDONED | new explicit RETRY | RUNNING with next ordinal/fence |
| SUCCEEDED | new run/retry/abandon | conflict |

Versions and per-job transition sequences start at1 and advance together. Attempt ordinals and
fences are positive signed64-bit values. Server times cannot regress. Exact key/payload replay
returns its original timestamp/version; it never rewrites history to match the current head.

## Execution, publication and uncertainty

Each new claim invokes actual INGEST → STRUCTURE → MAP → NORMALIZE → ASSERT. Immediately after
INGEST, actual hash/length must equal the arrival expectation before STRUCTURE can run. No extra
capture or fabricated transformation occurs. The original pinned semantic context, capture time,
run ID and resulting claim identities stay unchanged across retries; attempt/server lifecycle
identity is separate journal evidence. Empty input and unresolved values retain the prefix's
existing meaning; no unknown quantity is coerced to zero.

Atomic success locks the job head before source batches and execution bindings. It validates
active token/fence and full request/output metadata, then retains source bytes/snapshot/claims,
completed archive binding, the full current attempt receipt and successful job transition in one
transaction. There are no locks across executor I/O. The archive retains the first computation's
full receipt; the attempt retains its actual current full receipt, including completion time.
Same-attempt completion replay requires exactly that receipt and raw bytes, including on the
successful replay path. Reads lock the head for sharing while checking that its sequence references
the newest immutable transition; an internally consistent older head is an integrity failure.

Observed failures before publication retain a stable code/category and finite allowlisted diagnostic.
Raw exception text, source contents and driver/DSN details are never persisted as diagnostics.
Once publication begins, unavailable acknowledgement leaves the caller uncertain: it must not append
FAILED. A fresh read can show SUCCEEDED with all evidence or RUNNING; no rollback is inferred from
an error. A failure-journal outage likewise does not positively establish FAILED. Unavailable CLI
responses retain the validated scope/job ID and any acknowledged attempt ID for recovery. A lost
START acknowledgement cannot supply an attempt ID; inspect the scoped job before taking action.

RUNNING after a crash stays unresolved until a deliberate command. No lease/heartbeat timeout
proves process death. Abandonment requires the active attempt, expected version, command key,
actor and reason:

```bash
python -m procurement_intelligence_lab.interfaces.processing_jobs abandon \
  --scope scope.json --job-id JOB_ID --attempt-id ATTEMPT_ID --expected-version 2 \
  --command-key abandon-1 --actor developer --reason 'unresolved local attempt'
python -m procurement_intelligence_lab.interfaces.processing_jobs retry \
  --scope scope.json --job-id JOB_ID --command-key retry-1 --actor developer --expected-version 3
```

Abandonment invalidates the old publication right; it does not stop execution, undo I/O or prove
death. A stale success or failure writer cannot change a new attempt. Success and abandonment
serialize; the loser conflicts. These guarantees admit only the qualified local read-and-memory
prefix, not arbitrary future executors with external side effects.

## Recovery and evidence

`show`, `history`, `result` and `content` take `--scope` and `--job-id`, with no source/config flags.
After deleting the original source and every submission file, they recover only verified retained
evidence. `result` and `content` require positive success; `show` can truthfully return unresolved or
failed state. `content --output FILE` exports atomically without overwriting an existing path.

History is per job, ascending durable sequence, default100/max200 with exclusive nonnegative
`--after-sequence`. `has_more` comes from a real limit+1 query; there is no invented total or frozen
view across pages. Corrupt/missing linked evidence is integrity failure, not empty or not-found.
A returned page validates the evidence it returns; it does not claim all undisplayed records inspected.

New output separates `job_journal_receipt`, `attempt_execution_receipt`, `retained_execution_receipt`
and source `archive_receipt`. Run/retry responses also expose original `command_receipt`, per-call
`historical` and `observed_version`; these are not injected into immutable STARTED evidence.
Abandon responses label their `historical_command_receipt` separately from current state and expose
`receipt_is_current`/`observed_version`, so late replay cannot masquerade as abandoning a new attempt.
Legacy workflow-side-effect booleans are absent from the new receipt projection and unchanged on
old callers. There is no result cache or assertion of exactly-once physical invocation.

All failures use exit2, JSON stderr and empty success stdout. Acknowledged metadata/submission reads
use exit0 with explicit status/completion. Bounds: key1..256 characters; other identity/actor/reason
text1..4096; fixed-offset aware times; strict lowercase SHA256; exact nonnegative bytes/cursors;
history limit1..200; metadata files1MiB/32KiB; allowlisted graph16MiB/50,000 nodes/depth64. Oversize or
unknown data is rejected, never truncated, dynamically imported or unpickled. Caller actor labels
are provenance and do not constitute production authentication or new REVIEW/ACT permission.
