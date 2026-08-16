# ADR-022: Separate domain semantics from runtime implementation and physical planning

Status: accepted

## Context

The procurement pipeline is becoming a candidate vertical on a reusable evidence-first platform. A single configuration object that mixes stage meaning, procurement policy, provider selection, and orchestration would couple the domain to technologies, make provider comparisons change semantic configuration, and force a future control plane to understand Python authoring objects or domain names.

Optional stage sections also make it ambiguous whether a stage is not applicable, already satisfied, intentionally empty, or accidentally omitted. Conversely, one untyped identity/null transformer hides stage-specific guarantees and output behavior.

The repository already separates structure from mapping, assertions from truth, entity resolution from reconciliation, and domain semantics from adapters. The cross-domain design must preserve those boundaries while supporting source-specific execution and future provider swaps.

## Decision

Adopt the four-layer model described in [Domain packages and stage planning](../architecture/domain-package-and-stage-planning.md) as the platform contract. This decision ratifies the semantic boundary and schema rules. The deterministic compiler is implemented; the runtime registry/planner and a complete declarative procurement package are not.

1. platform-owned `StageDefinition` records define universal stage semantics, input/output contracts, guarantees, and allowed logical topology;
2. domain-owned declarative `StageBinding` records define mode, semantic requirements, domain config/policy references, and evaluation references, but do not normally select providers, models, services, or regions;
3. platform-defined strategy/policy contracts expose stable semantics that domains select and parameterize; and
4. deployment-owned `ImplementationConfig` and a runtime capability registry select and describe concrete implementations.

Use the stable logical pipeline `INGEST -> STRUCTURE -> MAP -> NORMALIZE -> ASSERT -> RESOLVE -> RECONCILE -> DERIVE -> DETECT -> PREDICT -> DECIDE -> ACT`. The platform owns allowed topology. Domain packages bind vertical requirements to it and do not define arbitrary DAG edges.

Keep a fixed `DomainPackage` meta-schema: every domain supplies every standardized stage binding. Use typed `EXECUTE`, `PASSTHROUGH`, and `EMPTY` modes plus stage-specific neutral semantics rather than omitted sections or an untyped null implementation.

Author domain packages as side-effect-free typed Python data. A `DomainCompiler` validates them and emits deterministic, language-neutral JSON containing stages, capabilities, requirements, and domain-owned references—not provider package names. Runtime/application configuration uses TOML plus environment/secret references; deployment mechanics use ecosystem-native YAML.

The repository layout mirrors this boundary. Shared contracts live under
`src/procurement_intelligence_lab/platform/`: `platform/domain_packages/` owns the stage catalog and
compiler, while `platform/semantics/` owns reusable evidence, identity, provenance, scope, ledger,
resolution, retrieval, reconciliation, state, and anomaly contracts. Vertical-owned records,
policy parameters, and algorithms live under `src/procurement_intelligence_lab/domains/<domain_id>/`.
The first vertical is `domains/procurement/`; a future vertical gets a sibling package rather than a
branch inside procurement code. Its authoritative semantic documentation lives under
`docs/domains/<domain_id>/`. The detailed ownership and dependency rules are in
[Platform semantics and vertical ownership](../architecture/platform-semantics.md).

Dependency direction is one-way: verticals may import the platform, but the platform does not
import a vertical; ports do not bind to a concrete vertical; and one vertical does not import a
sibling. Application composition is the boundary that may select and register vertical-specific
implementations. This corrects the whole-file classification introduced by PR #137 while preserving
the DomainPackage compiler and its manifest contract.

The control plane combines a compiled manifest, source profile, and runtime implementation registry/config to produce a physical plan. It may optimize neutral stages away physically, but semantic traces and provenance retain their explicit logical presence. A future Go control plane consumes compiled manifests and registry data; it does not import Python authoring objects or branch on domain identity.

Record the platform schema version, domain version, compiled-manifest hash, runtime implementation/provider/model versions, and application/code version separately in execution provenance.

## Consequences

- Procurement semantics remain stable while Docling/Textract, Splink/Semantica, model, service, or deployment selections are benchmarked and swapped.
- Capability validation can fail closed at compilation/startup when a selected implementation cannot satisfy a domain binding.
- Source profiles can choose execute or passthrough variants without changing the common downstream semantic contracts.
- Compiler determinism and manifest compatibility become platform contracts requiring conformance tests and migration rules.
- Stage-catalog evolution is an architecture change, not an ordinary domain edit.
- Adding a vertical-specific record does not make shared evidence, provenance, scope, or strategy
  contracts vertical-owned.
- The design introduces work for a meta-schema, procurement-package extraction, compiler/manifest, runtime registry and planner, SME/MCP authoring tools, and a second-vertical proof.

## Alternatives considered

### Optional stage sections

Rejected as the target because absence conflates not applicable, already satisfied, intentionally empty, and invalid/incomplete configuration.

### One generic identity or null transformer

Rejected because passthrough and empty behavior have stage-specific validation and output semantics. Typed neutral bindings may share helpers without erasing those meanings.

### Provider selection in `StageBinding`

Rejected because it couples portable domain semantics to runtime mechanics and makes a technology benchmark look like a domain-policy change.

### Domain-defined DAGs

Rejected for ordinary configuration because semantic order is a platform invariant. A genuinely different order requires a separate platform ADR.

## Adoption and validation

The stage catalog, fixed meta-schema, neutral modes, versioning rules, current-semantics mapping, and compiler conformance matrix are ratified in [the conformance contract](../architecture/domain-package-conformance.md). Implementation proceeds in separately gated roadmap slices: M0.34 compiles and validates manifests; M1-M4 extract the procurement package; M8 adds guarded authoring; and M9 adds runtime planning and a second-vertical proof.

Current repository types and application services remain authoritative for behavior on main until those slices are implemented and accepted. Provider choices remain evaluation hypotheses until supported by reproducible evidence.
