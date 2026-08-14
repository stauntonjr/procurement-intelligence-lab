# GitHub operating plan

## Source of truth

GitHub Issues and Project fields track work items; [milestone-map.md](milestone-map.md) tracks the relationship between delivery slices and the architecture. This file describes operating conventions and the forward-looking capability sequence. It is not a substitute for current implementation status.

Every implementation PR must:

1. identify one primary milestone and linked issue;
2. state whether it changes an invariant, boundary, or public contract;
3. update the milestone map when status or scope changes;
4. update the README, roadmap, or relevant ADR when the change makes existing documentation inaccurate;
5. include validation evidence, including documentation checks where applicable.

## Delivery sequence

The delivery sequence is intentionally vertical and may cross architectural layers:

- M0 Engineering & Architecture Harness — complete
- M1 Synthetic Document Vertical Slice — complete
- M2 Evidence Contract & Golden Tests — complete
- M3 Claims / Evidence Application Service — complete
- M4 Constrained Chat Routing — complete
- M5 Local HTTP Chat Inspector — in progress
- M6 Durable Identity, Source Viewer & Review Context — planned
- M7 Append-Only Persistence & Temporal State — planned
- M8 Retrieval Projections & Review UI — planned
- M9 Guarded Actions, Product Signals & Evaluation — planned

A milestone is complete only when its implementation, tests, documentation, and acceptance evidence are present.

## Project fields and views

Use a GitHub Project with fields: Status, Area, Type, Priority, Risk, Agentability, Evidence Required, Milestone, and Decision Needed. Views: milestone roadmap, evidence-gated queue, architecture decisions, and evaluation results. Keep labels focused on durable facets and use fields for workflow state to avoid duplication.

## Labels

Suggested labels are `area:architecture`, `area:domain`, `area:ingestion`, `area:provenance`, `area:entity-resolution`, `area:retrieval`, `area:ux`, `area:agents`, `area:evaluation`, `type:adr`, `type:feature`, `type:benchmark`, `type:docs`, `type:chore`, `risk:high`, `risk:medium`, `risk:low`, `evidence:required`, and `good-first-slice`. Milestones and Project fields carry sequencing and status.

## Initial queue

- Keep the semantic model and architecture invariants current.
- Maintain the evidence inspector contract and UX drill-down chain.
- Add stable identifiers before persistence or multi-document review.
- Define the synthetic data specification and evaluation manifests.
- Prefer small vertical issues with explicit acceptance evidence over speculative issue floods.

## Runner security

CI starts on GitHub-hosted runners. A future secure self-hosted DGX runner must be isolated, ephemeral or resettable, least-privilege, secret-free by default, and limited to trusted post-merge workflows. Untrusted public pull-request code is explicitly blocked from trusted self-hosted runners; public PRs use GitHub-hosted runners only.
