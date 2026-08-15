# Semantic model

```text
Artifact → [Structuring transformation event] → StructuredDocument
→ [Mapping transformation event] → MappedDocument → Normalized observations
→ Source Assertions → Entity Mentions → Entity Resolution Decisions
→ Canonicalized Assertions → Reconciliation → Operational State
→ Derived Facts → Anomalies → Predictions → Decisions → Actions
```

The proposed platform stage catalog names the schedulable semantics as:

```text
INGEST → STRUCTURE → MAP → NORMALIZE → ASSERT → RESOLVE
→ RECONCILE → DERIVE → DETECT → PREDICT → DECIDE → ACT
```

This naming does not remove intermediate contracts from the semantic model. Entity mentions, resolution decisions, canonicalized assertions, reconciliation decisions, and operational state remain explicit inputs/outputs within the corresponding stage boundaries. The platform owns this logical order; domains bind requirements to it rather than defining arbitrary stage edges. See [Domain packages and stage planning](../architecture/domain-package-and-stage-planning.md).

An Artifact is the immutable source boundary. Structure describes what was found; mapping assigns fields to a schema. Normalized observations make values comparable. Source assertions record claims plus source location, extraction method, confidence, timestamps, and epistemic status. They are not truth.

Each structuring or mapping transformation records an immutable provenance event with typed relationships to durable inputs, schemas, optional parent events, outputs, and the execution/component context. Deterministic transformations record implementation identity and version. Model-backed transformations also record provider, model ID, immutable model revision, prompt/template version, and schema version. Source assertions retain both their `EvidenceRef` and the originating transformation-event reference.

Entity Mentions and resolution decisions operate downstream of source assertions and upstream of canonical state. Reconciliation selects governing claims under explicit policy, retaining losing/conflicting claims and provenance. Every later layer carries EvidenceRefs back through the chain. Predictions, decisions, and actions are derived outputs with separate authority and review controls.

Execution provenance is an immutable directed acyclic event graph: a simple document path may have one parent, while reprocessing, human review, overrides, and shared inputs may introduce typed multi-parent relationships. It does not store raw prompts, secrets, hidden reasoning, or complete chat transcripts.

Logical stage order and execution-provenance graph shape are related but not identical. A physical planner may fuse or omit typed passthrough/empty work while the semantic trace still records every logical stage. Reprocessing and review can add event-graph branches without giving a domain package authority to change the platform's semantic topology.
