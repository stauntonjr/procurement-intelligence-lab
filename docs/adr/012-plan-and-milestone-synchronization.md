# ADR-012: Synchronize delivery plans with implementation

Status: accepted

## Context

The repository has two related but different planning needs:

- architecture documents describe durable boundaries, invariants, and trade-offs;
- GitHub milestones and PRs describe the incremental delivery sequence.

The original plan allowed these to drift because it described an ideal layer-by-layer architecture while implementation proceeded through vertical slices. Merged PRs had no explicit requirement to update status documents or record their milestone mapping.

## Decision

Use three complementary sources:

1. GitHub Issues and Project fields track actionable work and ownership.
2. `docs/development/milestone-map.md` is the canonical implementation-to-architecture status map.
3. ADRs and architecture documents record durable decisions, invariants, and public contracts.

Every implementation PR must name a primary milestone and issue. When scope or status changes, the PR must update the milestone map. When a boundary, invariant, or public contract changes, it must add or amend an ADR and update affected documentation.

Milestones are vertical delivery slices. They may cross multiple architectural layers. A milestone is complete only when implementation, tests, documentation, and acceptance evidence are present on `main`.

## Consequences

Agents can use the milestone map to orient before coding and to report status without reconstructing history from PRs. Documentation changes become part of the definition of done. The map introduces a small maintenance obligation, but prevents the more costly ambiguity between intended architecture and delivered capability.

This policy does not require an ADR for ordinary refactoring or every documentation edit. It requires an ADR when a durable architectural decision changes.

## Agent and review procedure

Before implementation:

- read the milestone map and relevant ADRs;
- choose or create the smallest vertical issue;
- state the expected documentation and acceptance evidence.

Before opening a PR:

- verify the milestone and issue are named;
- update the map if implementation status or scope changed;
- review README, roadmap, and related ADRs for stale claims;
- run the project checks and include their results.

After merge:

- mark the issue/milestone status consistently in GitHub;
- do not mark a milestone complete until its acceptance evidence is on `main`.
