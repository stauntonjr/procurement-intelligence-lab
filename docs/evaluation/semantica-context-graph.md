# Semantica Context Graph evaluation

Status: evaluate / POC. No adoption decision has been made, and Semantica is not a runtime dependency.

This note records a bounded evaluation of [Semantica AGI](https://github.com/semantica-agi/semantica), based on its current official [Context Module documentation](https://docs.getsemantica.ai/reference/context/), [capability overview](https://docs.getsemantica.ai/), and [getting-started documentation](https://docs.getsemantica.ai/getting-started/). These are vendor/project claims to verify experimentally, not claims that this repository has validated them.

## Why it is relevant

Semantica presents a graph-native context and accountability layer with:

- persistent agent memory and hybrid vector/graph retrieval;
- first-class decisions, causal chains, precedent search, policy checks, and explainable reasoning;
- entity linking, semantic deduplication, conflict detection, temporal validity, and provenance;
- GraphRAG/context retrieval, RDF/LPG graph support, export, visualization/Knowledge Explorer;
- MCP, REST, and CLI interfaces; and
- graph and vector integrations including Apache AGE and pgvector.

The official project also claims W3C PROV-O provenance and JSON/CSV/RDF export. PROV-O itself is the W3C recommendation for an OWL2 ontology expressing the PROV data model; interoperability must therefore be tested against the project’s exported artifacts, not inferred from a feature label. See the [W3C PROV-O recommendation](https://www.w3.org/TR/prov-o/).

## Two separate evaluation tracks

### DEV: derived developer context graph

Build a rebuildable projection over `AGENTS.md`, ADRs, architecture and domain docs, GitHub Issues/PRs, and selected evaluation artifacts. Test whether an agent can recover the rationale, constraints, provenance, and prior decisions needed to work safely across agents and sessions.

The repository and reviewed GitHub artifacts remain canonical durable engineering memory. Semantica would be a derived cache/projection that can be deleted and rebuilt from those artifacts. It must not become the only place a decision, requirement, or constraint exists.

Useful developer/QC/admin diagnostics include graph traversal, decision/precedent lookup, temporal views, provenance inspection, and Knowledge Explorer visualization. Explorer is not presumed to be the final claim-oriented procurement UI.

### APP: bounded capability benchmark

Evaluate Semantica behind project-owned ports and adapters for selected capabilities: PROV-O import/export, graph projection and query, GraphRAG grounding, temporal views, policy/reasoning, and entity linking/deduplication. The adapter must translate to the project’s domain contracts; Semantica must not redefine procurement semantics or become a direct dependency of the main runtime.

The critical semantic comparison is:

```text
source assertions (what a source claims)
        -> entity resolution (which identity a mention refers to)
        -> reconciliation (which claims govern operational state)
```

Semantica’s generic extraction, conflict-resolution, or deduplication pipeline may be useful infrastructure, but it cannot collapse these stages. Losing assertions, identity uncertainty, conflicting claims, governing-policy decisions, or evidence links is an evaluation failure even if a generic graph looks cleaner.

## Priority experiments

1. **PROV-O interoperability/export.** Create a small fixture with source documents, assertions, resolution decisions, and reconciliation outcomes. Compare Semantica’s exported RDF/JSON-LD (if supported by the tested build) with the project’s provenance model: identifiers, agents, activities, entities, derivation, attribution, timestamps, and round-trip preservation.
2. **Developer context graph.** Ingest a pinned, explicitly listed snapshot of repository/GitHub artifacts. Measure rationale-retrieval recall, citation/provenance completeness, stale-artifact detection, rebuildability, and cross-agent task comprehension against a repository-only baseline.
3. **Semantica + Apache AGE projection.** Verify the current AGE adapter/API in the tested build, project a bounded synthetic subset, and compare graph query expressiveness, rebuild time, correctness, and operational complexity with the project’s existing replaceable-projection boundary.

Entity resolution is a benchmark, not a trust decision. Compare a deterministic-ID baseline, Splink, Semantica, and later contextual/custom ER using precision, recall, false-merge rate, candidate recall, review rate, calibration, and runtime. Weight false merges as costlier than unresolved identities; abstention and human review are valid outcomes.

Under the proposed [domain-package architecture](../architecture/domain-package-and-stage-planning.md), Semantica, Splink, and project-owned resolvers are runtime implementation candidates. The procurement `RESOLVE` binding states provider-neutral requirements and policy/evaluation references; the runtime registry advertises and validates which candidate satisfies them.

## Adoption criteria

Adoption of any adapter or bounded use would require reproducible benchmark evidence showing:

- provenance survives import/export with stable, inspectable identifiers and acceptable PROV-O interoperability;
- source assertions, ER decisions, and reconciliation remain separately queryable and auditable;
- graph/vector projections are rebuildable and do not become canonical state;
- retrieval and reasoning improve a named DEV or APP task without unacceptable unsupported claims, stale context, or policy bypass;
- ER meets an agreed false-merge and review-load threshold against the deterministic and Splink baselines;
- APIs, licenses, deployment, observability, and failure behavior are acceptable for the bounded use; and
- the project can remove or replace Semantica through the port/adapter boundary.

## Rejection criteria

Reject the capability for the proposed use if it requires main-runtime coupling, silently overwrites or merges source claims, makes identity authoritative without benchmark evidence, cannot preserve provenance or temporal meaning, weakens fail-closed policy/review controls, prevents deterministic reproduction, or offers no material improvement over project-owned baselines. A failed experiment should leave the repository architecture unchanged.

## Decision

Keep Semantica in `evaluate / POC` status. Open a bounded issue for the experiments above when implementation capacity and fixtures are available. Do not add Semantica to application dependencies, production composition roots, or canonical storage in this documentation change.
