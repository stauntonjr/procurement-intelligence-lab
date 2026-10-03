# ADR-029: Exact brief review and idempotent save

Status: accepted for approved G2 #67/#68 continuation.

The graph is replaceable and cannot authorize persistence. Extend ADR-028 with a neutral
BriefStore port and immutable application review records. A separate SQLite adapter uses atomic
transactions to replace the active brief, bind immutable review receipts and save exactly once.
The initiating human is the required reviewer in the bounded demo. Review/save permissions are
supplied by a separate human composition root, never operational-model arguments.

A brief retains canonical deterministic core facts, exact request, run/version metadata and
snapshot. A new active version invalidates prior approval. Receipts have explicit configured TTL;
identical decision replay cannot extend it. Save revalidates current evidence and authority before
an atomic active-version/receipt check and unique idempotency write. Replaying a completed save
acknowledges that durable result, not a new action; changed evidence still fails.

Implement this contract before graph integration while provider/model selection is pending.
This changes delivery order only; it adds no domain policy or external actions. The CLI is a local
fixed-identity human boundary and must not be advertised as production authentication. Graph
checkpoint recovery and authenticated browser review remain later work. PostgreSQL can replace
the local adapter without moving approval authority into a framework.
