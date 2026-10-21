# ADR-043: Execute an explicitly bounded prefix of a validated package plan

Status: accepted. Decision [#225](https://github.com/stauntonjr/procurement-intelligence-lab/issues/225),
bounded implementation #226; [public contract](../architecture/package-execution.md).

## Context

ADR-022 separates declarative domain semantics, deployment selection and physical planning.
The existing planner admits a complete twelve-stage package while real BOM processing still uses
direct composition through ASSERT. Executing all advertised stages now would require additional
resolver/reconciler policy adoption; converting them to EMPTY would misstate the declaration.

## Decision

Introduce a synchronous runtime with an explicit INGEST-through-ASSERT execution boundary over
the unchanged complete plan. Composition injects exact stage executor registrations and resolved
policy/schema records; runtime admission validates every selected in-boundary registration before
source I/O. Each actual stage runs once and validates typed output, source/scope and provenance
continuity. Platform code has no procurement import or domain-name branching.

Retain all twelve logical entries in the returned execution receipt. The five executed stages
can succeed only with actual event/output evidence. Later entries are NOT_EXECUTED, including
unvisited neutral declarations; successful prefix completion never implies full package success.
Full-plan compatibility metadata outside the requested boundary does not prove executor
availability. Initially reject in-boundary neutral modes and unsupported wider execution before
I/O. Do not change existing manifest/planning schemas or silently shorten a requested boundary.

Keep the new trusted-local caller separate from existing BOM/archive/review/replay callers.
The receipt binds plan/config/policy/executor/source/context identities but is not a new durable
journal, result cache, production attestation or exactly-once guarantee. Scope, original claims,
unknown/empty distinctions, evidence and typed failure boundaries remain explicit.

## Alternatives and consequences

Full package execution is deferred pending remaining stage/policy acceptance. Continuing only
direct composition leaves the planner/executor gap unresolved. The proposed prefix makes one
real path executable and reusable, with additional admission, stage-aware transport and review
cost. Full-plan metadata remains required even for later unvisited stages; this preserves the
existing planner contract but must be labeled honestly in examples. Neutral execution and wider
boundaries need later acceptance rather than fabricated no-op results.

The [written specification](../superpowers/specs/2026-10-21-planned-prefix-execution-design.md)
defines required scenarios and the delivery boundary. The written spec and plan were approved;
implementation evidence remains revision-bound to normal review/qualification and delivery.
The bounded implementation does not complete the broader runtime or integrated-demo milestone.
