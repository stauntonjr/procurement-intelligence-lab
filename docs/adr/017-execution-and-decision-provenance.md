# ADR-017: Execution and decision provenance

Status: accepted

## Context

The repository needs to explain not only what evidence supported a result, but what execution environment and component produced it. Docker Compose and deployment configuration describe how services are orchestrated, but configuration files are mutable, environment variables can override them, and model aliases can resolve to different revisions.

Decision records therefore need an immutable, resolved reference to the execution that produced them. Deterministic components need implementation and policy identity even when no model is involved. Model-backed components additionally need provider, model ID, resolved model revision, prompt, and schema identity.

## Decision

Introduce two related contracts:

- ProvenanceContext is the normalized effective execution manifest. It contains the run ID, workflow identity, code revision, container image digest, effective configuration digest, dependency-lock digest, input snapshot IDs, start time, environment, and optional parent run.
- DecisionProvenance identifies the component that made a decision and links it to ProvenanceContext. It records whether the component was deterministic, model-based, or human; its implementation version; policy version; and, for model components, provider, model ID, resolved model revision, prompt version, and schema version.

The composition root or orchestrator creates ProvenanceContext from the resolved Docker Compose/configuration inputs and injects it into application services. Domain decision functions receive DecisionProvenance explicitly. Records retain the resolved provenance rather than relying on a mutable configuration path.

The local development fallback is explicitly marked with working-tree/local identities and is not production reproducibility evidence.

## Consequences

An anomaly, entity-resolution decision, reconciliation result, and later derived claim can be audited against both evidence and the execution/component that produced it. Re-running with a changed configuration, model revision, policy, or code revision yields distinct provenance identities.

Secrets and raw environment values must not be included in the manifest; only an allowlisted, sanitized environment fingerprint may be retained. External model providers must resolve mutable aliases to an immutable revision where the provider supports it.
