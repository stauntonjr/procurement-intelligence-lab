# G2 review-agent run and event foundation

Approved execution context: corpus implementation plan Task 5A, native execution with independent
review. Primary #70; part of #68/#72. Base 74321a81dff5d84bc4dededa94f4bed3028a4e01, stacked on PR175.

Contract: [run contract](../../product/review-agent-run-contract-v1.md), ADR-028.

- [x] RED: isolated same-example run/thread IDs, owned resume after reopened storage, permission and cross-scope/principal denial before lookup.
- [x] RED: exact event replay, altered/foreign/causally invalid events, timestamps and concurrent insertion.
- [x] Implement neutral dataclasses/RunStore, application service and SQLite adapter; no graph/model dependency.
- [x] RED: trajectory success requires real matching tool success and terminal event; omitted/error/foreign/conflicting events cannot pass; fixture/replay excluded from live metrics.
- [x] Implement evaluator and explicit allowlisted DTOs.
- [x] RED: create/resume in two CLI subprocesses, wrong project and malformed inputs; implement fixed-context CLI composition root.
- [x] Verify focused contracts/public caller, make check, clean installed CLI and challenges.
- [ ] Fresh independent review, revision-bound semantic evidence, commit/push stacked PR and synchronize handoff/Project.

Review focus: store authorization happens before state retrieval; metadata and event identities
cannot mutate via replay; event completeness is positive evidence; arbitrary event payloads do
not become public streams; SQLite concurrent replay cannot duplicate records; no fixture/live mix.
