# GitHub operating plan

## Source of truth

GitHub Issues and Project fields track work items; [milestone-map.md](milestone-map.md) tracks the relationship between delivery slices and the architecture. This file describes operating conventions and the forward-looking capability sequence. It is not a substitute for current implementation status.

Every implementation PR must:

1. identify one primary milestone and linked issue;
2. state whether it changes an invariant, boundary, or public contract;
3. update the milestone map when status or scope changes;
4. update the README, roadmap, or relevant ADR when the change makes existing documentation inaccurate;
5. include validation evidence, including documentation checks where applicable.

## Authoritative administration path

Agents administer GitHub planning from Codex with the keyring-backed `gh` session. Follow
[`.agents/skills/manage-github-planning/SKILL.md`](../../.agents/skills/manage-github-planning/SKILL.md); the
machine-readable expected state is [`.github/planning.json`](../../.github/planning.json).

The supported control surfaces are:

- `gh issue` for Issues, labels, milestones on Issues, dependencies, and native parent-child links;
- `gh label` and versioned `gh api` REST calls for repository labels and milestones;
- `gh project` for Project metadata, fields, membership, archive state, and item field values;
- `gh api graphql` for saved Project view create, update, delete, and verification;
- `tools/github_planning.py` for credential preflight, bounded audits, and idempotent view sync.

Run `python tools/github_planning.py audit` before and after a planning batch. The audit uses explicit
pagination and fails when configured fields, labels, milestones, or views are absent. Network denial
inside a managed sandbox requires an approved retry of the same command; it is not a product/API
limitation. Never place a token in repository files or command output.

## Canonical milestone sequence

GitHub owns the M0-M9 taxonomy:

- M0 Engineering & Architecture Harness
- M1 Synthetic Documents and Structure/Mapping
- M2 Assertion Ledger and Provenance
- M3 Deterministic Entity Resolution
- M4 Reconciliation and Governed State
- M5 Evidence-First Chat UX
- M6 Retrieval Projections
- M7 Intelligence & Forecasting
- M8 Guarded Agent Tools
- M9 Integrated Demo

Historical implementation order is recorded with `S` labels in `milestone-map.md`. A milestone is complete only when its implementation, layered tests, documentation, and Issue acceptance evidence are present.

## Project fields and views

Use a GitHub Project with fields: Status, Area, Work Type, Priority, Risk, Agentability, Evidence Required, Milestone, Decision Needed, Challenge ID, Semantic Surface, Test Layers, and Iteration. GitHub reserves the literal custom-field name `Type`, so `Work Type` is the portable project field name. Views: milestone roadmap, harness hardening, semantic challenges, review readiness, evidence-gated queue, architecture decisions, evaluation results, and drift. Keep labels focused on durable facets and use fields for workflow state to avoid duplication.

## Labels

Suggested labels are `area:architecture`, `area:domain`, `area:ingestion`, `area:provenance`, `area:entity-resolution`, `area:retrieval`, `area:ux`, `area:agents`, `area:evaluation`, `type:adr`, `type:feature`, `type:benchmark`, `type:docs`, `type:chore`, `risk:high`, `risk:medium`, `risk:low`, `evidence:required`, and `good-first-slice`. Milestones and Project fields carry sequencing and status.

## Initial queue

- Execute the M0 semantic-harness program in [Issue #109](https://github.com/stauntonjr/procurement-intelligence-lab/issues/109) and its #110-#117 work breakdown.
- Keep the semantic model and architecture invariants current.
- Maintain the evidence inspector contract and UX drill-down chain.
- Preserve stable identifiers across persistence adapters.
- Define the synthetic data specification and evaluation manifests.
- Prefer small vertical issues with explicit acceptance evidence over speculative issue floods.

Project field/view reconciliation is tracked by Issue #110. Branch/ruleset enforcement is tracked by Issue #111. Do not claim either live setting is complete from repository code alone; verify it with the authoritative administration audit after the required checks have appeared on a pull request.

## Runner security

CI starts on GitHub-hosted runners. A future secure self-hosted DGX runner must be isolated, ephemeral or resettable, least-privilege, secret-free by default, and limited to trusted post-merge workflows. Untrusted public-pull-request code is explicitly blocked from trusted self-hosted runners; public PRs use GitHub-hosted runners only.
