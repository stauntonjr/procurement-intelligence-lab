# GitHub operating plan

## Source of truth

GitHub Issues and Project fields track work items; [milestone-map.md](milestone-map.md) tracks the relationship between delivery slices and the architecture. This file describes operating conventions and the forward-looking capability sequence. It is not a substitute for current implementation status.

Every implementation PR must:

1. identify one primary milestone and linked issue;
2. state whether it changes an invariant, boundary, or public contract;
3. update the milestone map when status or scope changes;
4. update the README, roadmap, or relevant ADR when the change makes existing documentation inaccurate;
5. include validation evidence, including documentation checks where applicable.

## Canonical milestone sequence

GitHub owns the M0-M9 taxonomy:

- M0 Engineering & Architecture Harness
- M1 Synthetic Documents and Structure/Mapping
- M2 Assertion Ledger and Provenance
- M3 Entity Resolution
- M4 Reconciliation and Governed State
- M5 Evidence-first UX
- M6 Retrieval
- M7 Intelligence
- M8 Agent Tools and Guarded Workflows
- M9 Integrated Public Demo

Historical implementation order is recorded with `S` labels in `milestone-map.md`. A milestone is complete only when its implementation, layered tests, documentation, and Issue acceptance evidence are present.

## Project fields and views

Use a GitHub Project with fields: Status, Area, Type, Priority, Risk, Agentability, Evidence Required, Milestone, Decision Needed, Challenge ID, Semantic Surface, Test Layers, and Iteration. Views: milestone roadmap, harness hardening, semantic challenges, review readiness, evidence-gated queue, architecture decisions, evaluation results, and drift. Keep labels focused on durable facets and use fields for workflow state to avoid duplication.

## Labels

Suggested labels are `area:architecture`, `area:domain`, `area:ingestion`, `area:provenance`, `area:entity-resolution`, `area:retrieval`, `area:ux`, `area:agents`, `area:evaluation`, `type:adr`, `type:feature`, `type:benchmark`, `type:docs`, `type:chore`, `risk:high`, `risk:medium`, `risk:low`, `evidence:required`, and `good-first-slice`. Milestones and Project fields carry sequencing and status.

## Initial queue

- Execute the M0 semantic-harness program in [Issue #109](https://github.com/stauntonjr/procurement-intelligence-lab/issues/109) and its #110-#117 work breakdown.
- Keep the semantic model and architecture invariants current.
- Maintain the evidence inspector contract and UX drill-down chain.
- Preserve stable identifiers across persistence adapters.
- Define the synthetic data specification and evaluation manifests.
- Prefer small vertical issues with explicit acceptance evidence over speculative issue floods.

Project field/view reconciliation is tracked by Issue #110. Branch/ruleset enforcement is tracked by Issue #111. Do not claim either live setting is complete from repository code alone; verify it in GitHub after the required checks have appeared on a pull request.

## Runner security

CI starts on GitHub-hosted runners. A future secure self-hosted DGX runner must be isolated, ephemeral or resettable, least-privilege, secret-free by default, and limited to trusted post-merge workflows. Untrusted public-pull-request code is explicitly blocked from trusted self-hosted runners; public PRs use GitHub-hosted runners only.
