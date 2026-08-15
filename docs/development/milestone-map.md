# Delivery milestone map

GitHub milestones are the canonical delivery taxonomy. Historical vertical implementation sequence labels use `S` so they cannot be confused with milestone identifiers.

## Canonical GitHub milestones

| Milestone | Capability | Repository evidence | Status boundary |
|---|---|---|---|
| M0 | Engineering and architecture harness | CI, `AGENTS.md`, ADR-021, C001-C008 | In progress until Issue #3 and harness-hardening sub-issues satisfy acceptance |
| M1 | Synthetic documents and structure/mapping | XLSX adapter, fixtures, contract tests | In progress; Issue #7 remains authoritative |
| M2 | Assertion ledger and provenance | assertion ledger and execution provenance | In progress; milestone state lives in GitHub |
| M3 | Entity resolution | conservative resolver and retained decisions | In progress; broader acceptance remains issue-driven |
| M4 | Reconciliation and governed state | explicit precedence policy, expected/observed state | In progress; Issue #15 remains open |
| M5 | Evidence-first UX | chat, inspector, source/review context | In progress; Issue #8 remains open |
| M6 | Retrieval | rebuildable lexical projection lifecycle | In progress; follow-on adapters/evaluation remain open |
| M7 | Intelligence | evidence-backed anomaly taxonomy/orchestration | In progress |
| M8 | Agent tools and guarded workflows | planned issue slices | Planned |
| M9 | Integrated public demo | package smoke and future full walkthrough | Planned |

## Historical implementation slices

| Slice | Delivered capability | Primary evidence |
|---|---|---|
| S0 | Initial repository scaffold | PR #1 |
| S1 | Synthetic XLSX BOM vertical slice | PR #77 |
| S2 | Evidence contract | PR #79 |
| S3 | Claims/evidence application service | PR #80 |
| S4 | Constrained chat routing | PR #81 |
| S5 | Local HTTP inspector | PR #82 |
| S6 | Durable identifiers, source viewer, review context | PRs #86, #88, #90 |
| S7 | Ledger, state, anomalies, and execution provenance | PRs #92, #94, #105, #108 |
| S8 | Retrieval projection foundation | PR #101 |
| S9 | Guarded actions and integrated evaluation | Not delivered |

## Status rules

- A merged slice does not complete a GitHub milestone by itself.
- `Complete` requires implementation, layered tests, documentation, and issue acceptance evidence on `main`.
- Update GitHub Issue, milestone, Project, and this map together when state changes.
- Do not infer milestone status from branch names, PR numbers, or historical slice labels.
