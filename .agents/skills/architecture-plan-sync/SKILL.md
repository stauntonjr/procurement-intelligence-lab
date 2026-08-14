---
name: architecture-plan-sync
description: Keep repository architecture, delivery milestones, GitHub work items, and implementation status synchronized.
---

# Architecture plan synchronization

Use this skill whenever planning, implementing, reviewing, or reporting repository work.

## Before coding

1. Read `docs/development/milestone-map.md`.
2. Read `docs/development/github-plan.md` and the relevant architecture/ADR documents.
3. Identify the smallest vertical delivery slice.
4. Associate it with one primary milestone and GitHub issue.
5. Decide whether the change affects an invariant, boundary, or public contract.

## During coding

- Keep implementation and acceptance evidence together.
- Preserve the distinction between target architecture and capabilities on `main`.
- Do not infer milestone status from branch names or PR numbers.
- If the implementation sequence changes, update the milestone map in the same change.

## Before opening a PR

Confirm that the PR states:

- primary milestone and linked issue;
- implementation scope and acceptance evidence;
- tests/evaluation performed;
- documentation and ADR impact.

Update the README, roadmap, milestone map, or ADRs when the change makes them stale. Use an ADR for durable architecture decisions, not for routine status bookkeeping.

## Before declaring completion

A milestone is complete only when implementation, tests, documentation, and acceptance evidence are merged to `main`. Report any remaining drift explicitly.
