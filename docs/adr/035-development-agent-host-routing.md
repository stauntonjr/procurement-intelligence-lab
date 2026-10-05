# ADR-035: Development-agent host routing

Status: accepted in the PR reconciliation authorized on 2026-10-05.

## Context

PR #172 introduced named Mac planning and DGX implementation roles. Its review correctly
identified that the durable authority boundary needed an architecture record. Host and model
availability can change; a model-availability observation must not become a permanent constraint.

## Decision

Use `mac-planning-agent` for architecture review, cross-repository sequencing, issue decomposition,
acceptance design, and evidence planning. Use `dgx-implementation-agent` for source, tests,
documentation, packaging, CI, benchmarks, verification, and PR preparation in an isolated checkout.

The planning handoff names the governing Issue, source revision, touched contracts, acceptance
examples, evidence requirements, and unresolved decisions. The implementation agent re-grounds
the handoff against the current repository and records the resulting revision and evidence.
Explicit owner instructions may select another host or authorize integration and merge work.
Deployment and external actions still require authority from the owner; a planning handoff alone
does not grant it. These are development roles and confer no operational-agent authority.

## Consequences

The roles make handoffs and responsibility visible without coupling domain semantics to a host,
model, or orchestration framework. Verify current model availability when choosing the planning
surface. Keep review and implementation evidence tied to the revision under consideration.
