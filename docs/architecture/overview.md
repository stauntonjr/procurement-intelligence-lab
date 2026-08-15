# Architecture overview

The system has a semantic core, application use cases, ports, adapters, interfaces, observability, and evaluation. Ingestion is append-oriented and evidence-preserving. Canonical procurement state is a projection of governed assertions, never a replacement for the ledger.

The first vertical slice is synthetic XLSX/PDF BOM → structure → mapping → normalization → source assertions → simple deterministic resolution → canonical BOM → Postgres/CLI. Chat, agents, graph, forecasting, and fleet-scale claims are later milestones.

The ratified horizontal platform contract keeps that semantic sequence while making procurement a declarative domain package. Platform-owned stage definitions, domain-owned bindings and policy parameters, and deployment-owned implementation configuration remain separate. A compiler will emit a language-neutral manifest; a runtime planner will combine it with a source profile and capability registry without branching on the domain name. See [Domain packages and stage planning](domain-package-and-stage-planning.md), the [conformance contract](domain-package-conformance.md), the [domain vertical registry](domain-verticals.md), and [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md). The registry names procurement as the only active vertical and records the gate for the next one. This is an accepted contract, not a claim that the compiler or control plane is implemented.

## Boundaries

Core packages cannot import frameworks, databases, LLM SDKs, or UI code. Adapters implement ports. The composition root wires concrete dependencies. Search/vector/graph are replaceable projections.

Concrete extraction, entity-resolution, model, service, and deployment choices belong to runtime adapters/configuration. Domain packages state semantic requirements and policy references rather than provider package names.
