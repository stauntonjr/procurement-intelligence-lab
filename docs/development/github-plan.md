# GitHub operating plan

## Milestones

Create these milestones in order: M0 Engineering & Architecture Harness; M1 Synthetic Document Vertical Slice; M2 Assertion Ledger & Provenance; M3 Deterministic Entity Resolution; M4 Reconciliation & Operational State; M5 Evidence-First Chat UX; M6 Retrieval Projections; M7 Intelligence & Forecasting; M8 Guarded Agent Tools; M9 Integrated Demo.

## Project fields and views

Use a GitHub Project with fields: Status, Area, Type, Priority, Risk, Agentability, Evidence Required, Milestone, and Decision Needed. Views: M0 board, milestone roadmap, evidence-gated queue, architecture decisions, and evaluation results. Keep labels focused on durable facets and use fields for workflow state to avoid duplication.

## Labels

Suggested labels are `area:architecture`, `area:domain`, `area:ingestion`, `area:provenance`, `area:entity-resolution`, `area:retrieval`, `area:ux`, `area:agents`, `area:evaluation`, `type:adr`, `type:feature`, `type:benchmark`, `type:docs`, `type:chore`, `risk:high`, `risk:medium`, `risk:low`, `evidence:required`, and `good-first-slice`. Milestones and Project fields carry sequencing and status.

## M0 queue

- Establish repository constitution and architecture invariants.
- Establish semantic model and database conceptual model.
- Establish evidence inspector contract and UX drill-down chain.
- Establish ADR set and benchmark obligations.
- Establish Python/tooling/agent-loop conventions and CI.
- Define synthetic data specification and evaluation manifests.
- Create the first intentionally tiny M1 issue: parse one synthetic XLSX BOM into intermediate/domain structures and display or persist through CLI.

Only the small M1 epic and a bounded set of M2/M3/M5 epics should be created initially. Avoid speculative issue floods.

## Runner security

CI starts on GitHub-hosted runners. A future secure self-hosted DGX runner must be isolated, ephemeral or resettable, least-privilege, secret-free by default, and limited to trusted post-merge workflows. Untrusted public pull-request code is explicitly blocked from trusted self-hosted runners; public PRs use GitHub-hosted runners only.

