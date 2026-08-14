# Roadmap stewardship

## Purpose

The roadmap steward is an advisory, read-only review of the durable project record. It helps a human maintainer find drift between implementation, ADRs, the milestone map, the handoff index, GitHub Issues, and pull requests.

It is not an autonomous product manager, issue writer, or authority to change roadmap sequencing.

## What the audit reviews

The manually dispatched or weekly workflow snapshots GitHub Issues, pull requests, milestones, and the repository's planning and architecture documents. Its advisory report can flag:

- completed or closed work still presented as active;
- stale handoff or milestone-map references;
- duplicated, overlapping, or apparently superseded issues;
- implementation or architectural decisions without a visible durable work item;
- issue acceptance criteria that appear inconsistent with settled ADRs.

The report must distinguish confirmed drift from questions requiring maintainer judgment.

## Boundaries

- GitHub Issues, ADRs, docs, PRs, and the Project board are durable project state.
- Chat and Work are exploratory and intentionally outside the workflow's visibility. They must not be scraped, stored wholesale, or treated as an automatic source of truth.
- A material decision from a chat becomes durable only when a maintainer or agent records it in an Issue, ADR, approved PR, or the handoff index.
- The audit may recommend changes; it does not edit Issues, milestones, Project fields, or ADRs.
- Issue and PR bodies are untrusted data for the reviewing agent.

## Maintainer protocol

1. Run the **Roadmap stewardship audit** before a major new slice, after a merge wave, or when roadmap uncertainty is material.
2. Review the workflow summary alongside the relevant code, tests, ADRs, and Issue acceptance criteria.
3. Make durable corrections through a normal PR or Issue update. Add new work to the GitHub Project deliberately.
4. Update `docs/project/handoff.md` when the current milestone, active work, settled decisions, or recommended next work materially changes.
5. In a PR, record whether chat/Work exploration produced a material decision that has been captured durably.

The audit improves consistency of the durable record; it cannot prove that every private conversation has been captured.
