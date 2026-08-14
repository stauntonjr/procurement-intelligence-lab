# Delivery milestone map

This is the canonical map from the current implementation to the architecture. Milestones are delivery slices, not isolated layers; one slice may cross domain, application, adapter, test, and documentation boundaries.

| Milestone | Delivered capability | Status | Primary evidence |
|---|---|---|---|
| M0 | Repository harness, conventions, CI, invariants | Complete | `docs/architecture/invariants.md`, CI |
| M1 | Synthetic XLSX BOM vertical slice | Complete | `src/procurement_intelligence_lab/adapters/xlsx.py`, demo |
| M2 | Evidence contract and golden tests | Complete | `tests/unit/test_evidence_contract.py` |
| M3 | Claims/evidence application service | Complete | `application/evidence_service.py` |
| M4 | Constrained deterministic chat routing | Complete | `application/chat.py` |
| M5 | Local HTTP chat/evidence inspector | Complete | [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82) |
| M6 | Durable identifiers, source viewer, and review context | In progress | [Issue #85](https://github.com/stauntonjr/procurement-intelligence-lab/issues/85), ADR-013 |
| M7 | Append-only persistence and temporal/as-of state | Planned | Ledger schema, migrations, rebuildable projections |
| M8 | Retrieval projections and review UI | Planned | Labeled retrieval evaluation and review workflows |
| M9 | Guarded actions, product signals, and integrated evaluation | Planned | Approval gates, sanitized feedback loop, release evidence |

## Status rules

- **Planned** means the capability is not yet implemented on `main`.
- **In progress** means an open PR or active implementation exists.
- **Complete** means implementation, tests, documentation, and acceptance evidence are present on `main`.
- A merged PR may complete only part of a milestone; update this table when that happens.
- If the implementation sequence changes, update this map and the GitHub operating plan in the same PR.

## PR mapping

The merged implementation sequence is:

- M1: PR #77
- M2: PR #79
- M3: PR #80
- M4: PR #81
- M5: PR #82
- M6: Issue #85, implementation in progress

This mapping is deliberately explicit so future agents do not infer milestone status from PR numbers or filenames.
