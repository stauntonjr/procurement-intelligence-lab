# ADR-018: Rebuildable retrieval projections behind a lifecycle port

Status: accepted

## Context

Lexical, vector, and graph retrieval can accelerate investigation, but none may become an independent source of truth. The append-only assertion ledger remains canonical, and every retrieval result must retain source and epistemic context.

The first retrieval slice needs explicit build, rebuild, version, freshness, failure, and deletion semantics without selecting a vector database, graph store, or production search service.

## Decision

Define a typed RetrievalProjection port. A build receives only canonical AssertionLedgerEntry records and a versioned build request. It produces an immutable manifest containing the projection identity, kind, implementation version, configuration digest, source entry IDs, source as-of time, lifecycle status, and record time.

Only a ready projection may serve results. Failed or deleted projections must reject retrieval rather than silently serving stale content. Results retain their ledger entry, source assertion, evidence, projection-manifest identity, score, and epistemic status.

The dependency-free reference adapter is an in-memory lexical projection. Vector and graph adapters remain future replaceable implementations of the same port.

## Consequences

Projection state is derived and rebuildable from assertion history. A future adapter may use a search, vector, or graph system, but must preserve manifest and lifecycle semantics. The port does not choose a durable canonical database, implement generic event sourcing, or establish retrieval quality; benchmark and adapter-selection work remains separate.
