# Architecture overview

The system has a semantic core, application use cases, ports, adapters, interfaces, observability, and evaluation. Ingestion is append-oriented and evidence-preserving. Canonical procurement state is a projection of governed assertions, never a replacement for the ledger.

The first vertical slice is synthetic XLSX/PDF BOM → structure → mapping → normalization → source assertions → simple deterministic resolution → canonical BOM → Postgres/CLI. Chat, agents, graph, forecasting, and fleet-scale claims are later milestones.

## Boundaries

Core packages cannot import frameworks, databases, LLM SDKs, or UI code. Adapters implement ports. The composition root wires concrete dependencies. Search/vector/graph are replaceable projections.

