# ADR-017: Execution, decision, and transformation provenance

Status: accepted

## Context

The repository needs to explain not only what evidence supported a result, but what execution environment and component produced it. Docker Compose and deployment configuration describe how services are orchestrated, but configuration files are mutable, environment variables can override them, and model aliases can resolve to different revisions.

Decision records therefore need an immutable, resolved reference to the execution that produced them. Deterministic components need implementation and policy identity even when no model is involved. Model-backed components additionally need provider, model ID, resolved model revision, prompt, and schema identity.

Source/evidence provenance and execution provenance answer different questions. Evidence identifies what a source artifact said and where it said it. Execution provenance identifies which transformation or decision produced a derived runtime object. Neither replaces the other.

## Decision

Introduce three related contracts:

- `ProvenanceContext` is the normalized effective execution manifest. It contains the run ID, workflow identity, code revision, container image digest, effective configuration digest, dependency-lock digest, input snapshot IDs, start time, environment, and optional parent run.
- `DecisionProvenance` identifies the component that made a transformation or decision and links it to `ProvenanceContext`. It records whether the component was deterministic, model-based, or human; its implementation version; policy version; and, for model components, provider, model ID, resolved model revision, prompt version, and schema version.
- `TransformationEvent` is an immutable event for structuring or mapping. It records typed relationships to durable inputs and schemas, output IDs, optional parent events, and the responsible `DecisionProvenance`. The event graph supports multiple inputs and branching; a single-parent path remains straightforward.

The composition root or orchestrator creates `ProvenanceContext` from the resolved Docker Compose/configuration inputs and injects it into application services. Domain decision functions receive `DecisionProvenance` explicitly. Records retain the resolved provenance rather than relying on a mutable configuration path.

The initial vertical slice records the deterministic XLSX BOM structurer's source-artifact hash, implementation version, schema version, execution context, structured output, and event ID. Assertions emitted from that result retain the event ID in addition to their `EvidenceRef`.

The local development fallback is explicitly marked with working-tree/local identities and is not production reproducibility evidence.

## Consequences

An anomaly, entity-resolution decision, reconciliation result, and later derived claim can be audited against both evidence and the execution/component that produced it. Re-running with a changed configuration, model revision, policy, code revision, parser implementation, prompt, or schema yields distinct provenance identities.

Secrets and raw environment values must not be included in the manifest; only an allowlisted, sanitized environment fingerprint may be retained. External model providers must resolve mutable aliases to an immutable revision where the provider supports it. Raw prompts, hidden reasoning, and complete chat transcripts are not provenance payloads.

Relational foreign keys may persist event/context references, but the conceptual model is an immutable directed acyclic graph rather than a linked list or a required graph database.
