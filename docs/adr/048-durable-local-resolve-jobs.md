# ADR-048: Durable local RESOLVE jobs with pinned catalog evidence

Status: proposed; not owner-approved and not implemented. Primary M1,
[Issue #244](https://github.com/stauntonjr/procurement-intelligence-lab/issues/244), parent #36.
[Written proposal](../superpowers/specs/2026-10-25-resolved-prefix-jobs-design.md).

## Context

ADR045 delivers fenced local jobs only through ASSERT. ADR046 executes and atomically retains a
six-stage RESOLVE computation but explicitly leaves six-stage job integration to a later contract.
The owner selected durable RESOLVE jobs as the next runtime direction after PR243. Existing job
records validate exact five-stage types, metadata, snapshots and codecs; widening them in place
would violate their frozen request and evidence contract.

## Proposed decision

Add a distinct `local_resolved_prefix_jobs/v1` capability, recipe and public caller. Pin the full
existing first-five definition plus exact catalog audit bytes, resolution policy and sixth-stage
registration metadata. Preserve ADR045 explicit FIRST/RETRY/abandon/fence/acknowledgement semantics
and ADR046 matching/abstention unchanged. New profile-local job/attempt/transition identities and
arrival uniqueness do not redefine old jobs or imply a global event registry.

Only newly acknowledged attempts execute the actual six registered stages. Inject the existing
arrival guard immediately after INGEST, before STRUCTURE. Retain source, first-five archive,
resolved archive/catalog and the full actual-attempt success in one transaction after locking
and validating the active job fence. Use a transaction-scoped resolved archive helper without
changing the existing public archive behavior. Distinguish actual current receipts from every
first-retained prefix/resolved receipt during completion replay and source-free recovery.

Core owns immutable typed definitions, lifecycle and complete input/output binding. Ports are
framework-independent; Postgres owns mechanics; bootstrap selects current implementations. An
explicit new capability requires initialized source/prefix/resolved archives and never initializes
old jobs or migrates old records. Current-executor preparation is unnecessary for historical replay
and retained reads. Unknown acknowledgement and crashed RUNNING remain unresolved evidence.

## Alternatives and consequences

Widening v1 changes frozen semantics. Chaining independent ASSERT and RESOLVE jobs loses one atomic
six-stage success. A separate profile costs typed bindings, additive storage, real concurrency and
fault qualification, installed/public proof and frozen legacy comparisons. It introduces no new
identity algorithm, model, queue, lease, automatic retry, RECONCILE job, external side effect or
operational-agent authority. Broader #36/#14/#39/#43/#45 and linked Issue criteria remain open.

Approval of this proposal authorizes implementation planning; design/review alone does not establish
runtime or main acceptance. The Issue and final implementation receipt must record those separately.
