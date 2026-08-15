# Roadmap

## 0. Portfolio slice (this repository)

- Establish an evidence-first domain model.
- Demonstrate deterministic normalization, resolution, retrieval, anomaly detection, and approval gating.
- Make non-claims and evaluation boundaries explicit.
- Enforce semantic contracts with layered CI, clean-artifact smoke tests, and C001-C008 development-agent challenges.

## 1. Discovery-ready prototype

- Add a small relational store with migrations and typed contracts.
- Add document chunking with page/section coordinates and content hashes.
- Compare lexical retrieval with an embedding-backed index on a labeled query set.
- Add a review UI for resolution candidates and anomaly explanations.

## 2. Team-scale pilot

- Introduce connectors behind per-source adapters and replayable ingestion jobs.
- Add temporal event modeling and late-arriving correction handling.
- Calibrate risk scores by project phase and measure alert burden.
- Integrate identity, authorization, secrets rotation, and centralized audit storage.

## 3. Production hardening

- Define SLOs, data retention, deletion, lineage, and incident response.
- Load test ingestion and retrieval with representative—not fabricated—volumes.
- Run red-team exercises against prompt injection, cross-tenant access, and action replay.
- Gate rollout on offline and shadow-mode evaluation, not demo quality.

## Horizontal domain-platform workstream (proposed)

This cross-cutting sequence turns procurement from the only vertical into a declarative package on a reusable platform. It is target architecture under [ADR-022](docs/adr/022-domain-semantics-and-physical-stage-planning.md), not implemented capability on `main`.

1. Define the platform stage catalog, fixed `DomainPackage` meta-schema, typed neutral modes, strategy/policy contracts, and canonical manifest schema.
2. Extract procurement requirements, source profiles, policies, and evaluation references into the first domain package without changing observable behavior.
3. Build a deterministic compiler and language-neutral JSON manifest with validation, compatibility, and reproducibility tests.
4. Load runtime implementation descriptors/config, validate capabilities, and plan optimized physical execution while retaining complete semantic traces.
5. Add SME and MCP authoring/validation tools that produce declarative domain data without I/O or executable domain callbacks on import.
6. Prove the horizontal boundary with a second vertical, shared stage conformance tests, and provider-swap benchmarks.

Concrete providers, models, services, regions, and orchestration products remain runtime evaluation choices rather than domain-package semantics.
