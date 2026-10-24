# ADR-045: Durable local prefix jobs with explicit fenced attempts

Status: accepted by owner on 2026-10-23; approved proposal `da09f98`. Decision [#231](https://github.com/stauntonjr/procurement-intelligence-lab/issues/231),
primary M1, parent #36. The owner approved the written lifecycle policy and instructed proceed.
Implementation #232 has an owner-approved plan (`6dc1522`); implementation is in progress; no runtime acceptance is delivered. [Approved specification](../superpowers/specs/2026-10-23-local-prefix-jobs-design.md).

## Context

ADR043 executes the qualified actual INGEST-through-ASSERT prefix; ADR044 atomically retains
its complete plan/receipt and original source evidence. Computation retention deliberately does
not represent submission, running/failed attempts, request idempotency or recovery authority.
#36 calls for event/job/attempt/retry/idempotency contracts while keeping a local synchronous path.
A restart must not turn missing acknowledgement into failure or authorize another active writer.

## Decision

Add an explicit durable local job profile around the existing prefix, separate from unchanged
execution/archive callers. Freeze a declared arrival's expected bytes and full admitted request,
plan/config/policy/metadata. Exact scope+idempotency key returns the same job only when full
canonical request content agrees; different content conflicts. Submission performs no source I/O.
No implicit source/version selection, config upgrade or provider fallback.

An append-oriented journal and neutral port record explicit FIRST/RETRY attempts, classified
failures, success and abandonment; a validated mutable head provides per-job version/fence CAS.
Only a newly acknowledged claim executes. Command keys are supplied explicitly; replay returns
historical acknowledgements without executing again. A failed or abandoned attempt needs a new
manual retry command. Preserve pinned semantic execution context across attempts to preserve
assertion IDs; store actual attempt identity/server lifecycle times separately.

Verify the actual captured hash/length against the arrival immediately after INGEST. A successful
attempt's full current receipt and first-retained archive receipt commit atomically with existing
source content/snapshot/claim membership and the job success transition. A lost completion
acknowledgement does not authorize writing FAILED. Typed failures before publication can be
recorded as failures; unavailable journal acknowledgement remains uncertain.

Explicit abandonment fences an unresolved attempt's publication right; it does not prove death,
undo I/O or hard-cancel computation. Check the active fence before any source/result write in the
same completion transaction. Abandonment and success serialize: the loser conflicts. No timeout
expiry, leases, automatic retries, queue or external-side-effect guarantee.

Add additive explicit local_prefix_jobs/v1 initialization on supported archive capabilities.
Postgres owns mechanics; core owns transitions/identity and imports no DB/framework/procurement.
Stored input/receipt graphs remain bounded/allowlisted and contain no secrets or callables.
Scoped reads reconstruct stored evidence without current source/config/executor I/O. The new
trusted developer interface grants no authority to operational agents and changes no existing
approval/tool policy under #41/#68/#70. Original assertions and broader Issue acceptance remain.

## Alternatives and consequences

In-memory contracts alone cannot prove restart handling. A distributed listener/queue/worker
system adds unapproved scheduling and side-effect policy. The local journal is a vertical slice
with meaningful state/fencing/atomicity cost, not generic application-wide event sourcing.
It requires real concurrency/crash/fault/codec/public/installed-artifact tests and independent
review before delivery. #36 stays open for broader ingestion, worker and partial-stage semantics;
#13/#21/#33/#35/#37/#41/#68/#70/#75 are not completed by this decision.

The owner approved this policy in written proposal `da09f98`. The [implementation plan](../superpowers/plans/2026-10-23-local-prefix-jobs.md)
for #232 is owner-approved at `6dc1522`; implementation is in progress; no current main runtime or storage behavior changes in this decision record.
