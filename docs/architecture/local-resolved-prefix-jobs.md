# Durable local RESOLVE jobs

[#244](https://github.com/stauntonjr/procurement-intelligence-lab/issues/244) / accepted ADR048
adds a distinct `local_resolved_prefix_jobs/v1` profile around the existing actual six-stage
runner. [The approved design](../superpowers/specs/2026-10-25-resolved-prefix-jobs-design.md) and
[implementation plan](../superpowers/plans/2026-10-25-resolved-prefix-jobs.md) govern the boundary.
Implementation qualification/main delivery live in the Issue, not an inference from this page.

## Explicit initialization and admission

Install the optional storage extra and set `PIL_ASSERTION_ARCHIVE_DSN` in the environment. Explicitly
initialize source, prefix, resolved and the new journal capabilities in that order. This does not
require, initialize or widen the original five-stage local job capability.

```sh
python -m procurement_intelligence_lab.interfaces.assertion_archive init
python -m procurement_intelligence_lab.interfaces.planned_execution_archive init
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive init
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs init
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs submit source.xlsx \
  --arrival arrival.json --context context.json --manifest manifest.json \
  --registry registry.json --config config.toml --normalization-policy normal.json \
  --resolution-policy resolve.json --candidate-snapshot catalog.json \
  --stop-after RESOLVE --idempotency-key request-1
```

The manifest is the compiled procurement package. Pin the six actual registered implementations
and exact config/code/context versions, timestamps and four-field source scope. All selection
settings and context environment must be empty. The existing
[resolved execution inputs](planned-resolve-prefix.md) provide strict policy/catalog schemas and
synthetic fixture examples; the [original job contract](local-prefix-jobs.md) defines arrival JSON.
No source capture occurs during submission. The frozen request contains actual raw catalog bytes,
semantic candidate identity, normalization/resolution policies, implementation metadata and all
first-five pins. Admission completes before constructing storage.

The recipe is `procurement.bom-local-resolved-prefix@1`. Job/attempt/transition ID namespaces begin
`local-resolved-prefix-`; old five-stage IDs are rejected by the new caller and vice versa.
Idempotency and arrival uniqueness are profile-local and exact-scope. Same key plus changed raw
catalog bytes conflicts even if JSON whitespace/order leaves catalog semantic identity unchanged.
Different keys remain different jobs and may share first-retained computation evidence. There is
no new global arrival registry, implicit catalog selection or policy/provider fallback.

## Explicit attempts, fencing and acknowledgement

```sh
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs run \
  --scope scope.json --job-id JOB_ID --command-key first --actor developer --expected-version 1
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs abandon \
  --scope scope.json --job-id JOB_ID --attempt-id ATTEMPT_ID --command-key abandon-1 \
  --actor developer --expected-version 2 --reason 'unresolved local attempt'
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs retry \
  --scope scope.json --job-id JOB_ID --command-key retry-1 --actor developer --expected-version 3
```

Only a newly acknowledged FIRST/RETRY executes. Exact command replay returns historical evidence
without source/config/current-executor preparation and grants no new invocation. Retry requires
FAILED or ABANDONED, a new explicit key and current version. START keys cannot change intent,
actor, version or payload. Abandon requires the exact active attempt; it fences publication and
does not prove process death, cancel execution or undo I/O. RUNNING after a crash stays unresolved.

A new attempt actually invokes INGEST/STRUCTURE/MAP/NORMALIZE/ASSERT/RESOLVE. Actual arrival bytes
are checked immediately after INGEST, before STRUCTURE. Pinned semantic context/capture/run/catalog
stay fixed across attempts; server lifecycle/attempt identity stays separate. Matching and
abstention are unchanged: empty documents still execute six stages; missing/ambiguous identity
can produce a successful job with unresolved outcomes, never invented canonical links or zero.
All twelve dispositions remain visible; RECONCILE through ACT are NOT_EXECUTED and package
completion is false.

The completion transaction locks/checks the latest job head and active fence before writing any
source/result. Source content/snapshot/claims, first-five archive, resolved archive/catalog, full
actual attempt result and journal success commit together. There is no lock over executor I/O.
Stale success/failure cannot overwrite a newer attempt; success and abandonment serialize.
Exact completion replay must agree on the full current receipt and raw bytes, not only digest.

Pre-publication failures retain finite sanitized code/category/diagnostic. Unknown START or
completion acknowledgement, or unavailable failure journaling, never establishes FAILED. Inspect
the scoped job; do not infer rollback or automatically retry. Unavailable public responses retain
known scope/job and acknowledged attempt IDs, without inventing an ID after lost START ack.

## Recovery and receipt roles

`show`, `history`, `result` and `content` need only scope/job identity. The source, catalog and all
submission files can be removed after success; retained recovery validates linked evidence without
current executor construction. Corrupt/missing records, checksums, links or a stale head are typed
integrity failure, not success/empty/not-found. Result/content require positive successful evidence.

```sh
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs show --scope scope.json --job-id JOB_ID
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs history --scope scope.json --job-id JOB_ID --limit 100 --after-sequence 0
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs result --scope scope.json --job-id JOB_ID
python -m procurement_intelligence_lab.interfaces.resolved_processing_jobs content --scope scope.json --job-id JOB_ID --output recovered.xlsx
```

History is per-job ascending sequence, default100/max200, exclusive nonnegative cursor and real
limit+1 `has_more`. It asserts no global total or frozen view. Content export is atomic and refuses
an existing output path. The separate current/first receipts remain visible:

| Field | Evidence role |
|---|---|
| `job_journal_receipt` | Actual recorded transition |
| `command_receipt`, `historical`, `observed_version` | Original START acknowledgement and this call's observation |
| `attempt_execution_receipt` | Full current attempt's six-stage receipt |
| `attempt_prefix_execution_receipt` | That attempt's embedded first five |
| `retained_execution_receipt` | First retained six-stage computation |
| `retained_embedded_prefix_execution_receipt` | Its own embedded first five |
| `retained_prefix_execution_receipt` | First independently retained first-five computation, possibly earlier |
| `archive_receipt` | Resolved archive identity with its nested prefix/source linkage |

A prior archive record can differ in completion time or catalog raw representation from the
current attempt. Its receipt is never relabelled as a new invocation. Legacy journal/cache-side-
effect booleans are absent from these new projections. Abandon replay likewise labels its
historical command separately from the current head. No exactly-once physical invocation is claimed.

Success/metadata returns exit0; failures return exit2 with sanitized JSON stderr and empty success
stdout. Existing archive/execution errors keep their typed categories, while new job failures use
`resolved_prefix_job_*` codes. Input bounds follow the approved design: metadata1MiB, context/
arrival/policies/catalog32KiB, graph16MiB/50,000 nodes/depth64, catalog0..256 keys, bounded Unicode
keys/text and signed64bit counters. Unknown/oversized input fails; it is never truncated.

This is a trusted local developer interface. It introduces no production authentication,
operational-agent authority, listener/queue/lease, automatic retry, RECONCILE job, seven-stage flow
or broad entity-resolution quality claim. Broader #36/M3 acceptance remains open.
