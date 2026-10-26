# Architecture overview

The system has a semantic core, application use cases, ports, adapters, interfaces, observability, and evaluation. Ingestion is append-oriented and evidence-preserving. Canonical procurement state is a projection of governed assertions, never a replacement for the ledger.

The initial vertical used synthetic XLSX BOMs. The current package executes a bounded XLSX prefix
through RESOLVE and a separate RECONCILE operation over retained producers; fresh seven-stage
orchestration remains subsequent work. The evidence-review showcase is a separate delivered path.
Forecasting and fleet-scale claims remain outside the qualified package execution boundary.
See the [shared semantic vocabulary and runtime limits](semantic-model.md),
[planned RESOLVE prefix](planned-resolve-prefix.md) and [retained reconciliation](retained-reconciliation.md).

The ratified horizontal platform contract keeps that semantic sequence while making procurement a declarative domain package. Platform-owned stage definitions, semantic contracts, and strategy interfaces; domain-owned bindings, records, policy parameters, and algorithms; and deployment-owned implementation configuration remain separate. The deterministic compiler emits a language-neutral manifest; the runtime planner combines it with a source profile and capability registry without branching on the domain name. See [Platform semantics and vertical ownership](platform-semantics.md), [Domain packages and stage planning](domain-package-and-stage-planning.md), the [conformance contract](domain-package-conformance.md), the [domain vertical registry](domain-verticals.md), and [ADR-022](../adr/022-domain-semantics-and-physical-stage-planning.md). The registry names procurement as the only active production vertical and records the gate for the next one; that classification does not establish production readiness.

## Boundaries

Core packages cannot import frameworks, databases, LLM SDKs, or UI code. Adapters implement ports. The composition root wires concrete dependencies. Search/vector/graph are replaceable projections.

Concrete extraction, entity-resolution, model, service, and deployment choices belong to runtime adapters/configuration. Domain packages state semantic requirements and policy references rather than provider package names.

Shared semantic contracts live under `platform/`; procurement-owned BOM, BoQ, PO, state,
reconciliation, and anomaly behavior lives under `domains/procurement/`. Platform and ports never
import a concrete vertical.
