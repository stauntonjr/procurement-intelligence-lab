# Semantic model

```text
Artifact → StructuredDocument → MappedDocument → Normalized observations
→ Source Assertions → Entity Mentions → Entity Resolution Decisions
→ Canonicalized Assertions → Reconciliation → Operational State
→ Derived Facts → Anomalies → Predictions → Decisions → Actions
```

An Artifact is the immutable source boundary. Structure describes what was found; mapping assigns fields to a schema. Normalized observations make values comparable. Source assertions record claims plus source location, extraction method, confidence, timestamps, and epistemic status. They are not truth.

Entity Mentions and resolution decisions operate downstream of source assertions and upstream of canonical state. Reconciliation selects governing claims under explicit policy, retaining losing/conflicting claims and provenance. Every later layer carries EvidenceRefs back through the chain. Predictions, decisions, and actions are derived outputs with separate authority and review controls.

