# ADR-028: Application-owned review-agent runs and audit

Status: accepted for the approved G2 foundation slice (#70; part of #68/#72).

## Context

The corpus service is verified on PR #175. An operational agent needs reproducible, isolated
execution records before graph construction. ADR-014's preview is non-persistent. Graph state
and hosted telemetry cannot grant review or save authority.

## Decision

Application services issue fresh run, query, attempt and thread IDs. An immutable run binds the
initiating principal, tenant/project/site, UTC creation time, execution kind and version metadata.
Resume authorizes the caller before a scoped store lookup; unknown and foreign runs share the
same not-found result. Retry resumes the existing binding rather than creating a new thread.

A neutral RunStore port owns immutable run records and append-only typed events. A stdlib SQLite
adapter provides local durability, transactional uniqueness and exact-event replay idempotency.
This is a demo application ledger, not the canonical procurement assertion store. PostgreSQL
remains the intended production store; the port permits replacement without graph/domain changes.
No graph or third-party dependency enters the semantic layer.

Public events use a fixed field catalog, with no arbitrary document/model text. Terminal tool
results reference evidence snapshots through IDs. Causal event identity and tool name/version
must match the actual invocation. The evaluator counts successful tool results separately from
requests: absent/partial events are unknown, observed failures or contradictory events fail,
and excluded fixture/replay examples never contribute to live metrics.

This foundation exposes a local CLI create/resume boundary. Its principal and permissions come
from fixed demo configuration, not request arguments. HTTP/authenticated human decisions,
brief persistence, approval expiry, save idempotency and graph checkpointing are subsequent G2
slices governed by #53/#66/#67/#68. Run/thread correlation IDs grant no authority.

## Consequences

Concurrent examples cannot share a thread accidentally. Independent Python processes can resume
an owned run and read the same ledger. SQLite lock/write errors remain infrastructure failures;
unknown records are not converted into empty successful traces. No live inference or approved
brief-save claim follows from this foundation.
