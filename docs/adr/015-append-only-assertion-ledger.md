# ADR-015: Append-only assertion ledger behind a port

Status: accepted

## Context

Source assertions are the preserved record of what an artifact said before entity resolution, reconciliation, or derived intelligence. The architecture requires canonical state to be a rebuildable projection of governed assertions, but the current lab has no persistence dependency.

The next slice must establish the boundary without prematurely choosing Postgres schemas, an ORM, or a hosted service.

## Decision

Define an outbound `AssertionLedger` protocol for appending and reading source assertions. Each ledger entry has:

- a stable assertion identifier;
- a monotonically increasing sequence within the ledger;
- an observation timestamp;
- the immutable source assertion.

The reference adapter is an in-memory append-only implementation. It supports ordered reads and inclusive as-of reads. It exposes no update or delete operation. Timestamps must be timezone-aware.

A future durable adapter may use Postgres or another store, but it must preserve the append-only contract and rebuildable-projection semantics.

## Consequences

The semantic core and application services can depend on a small typed port while adapters own storage mechanics. Tests can validate temporal and ordering semantics without a database. The in-memory adapter is not a production durability claim; it is a contract reference and composition-root fixture.

Schema design, migrations, correction events, retention, and transactional guarantees remain separate decisions for the durable adapter.
