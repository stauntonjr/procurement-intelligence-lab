# Technology evaluation register

This register records technologies under evaluation. Entries are not adoption decisions; accepted architecture and benchmark evidence remain authoritative.

Where a technology implements a standardized pipeline capability, evaluate it as a deployment-owned implementation descriptor behind the runtime registry. The portable domain package retains capability requirements, policy/config references, and evaluation references—not provider names. See [Domain packages and stage planning](../architecture/domain-package-and-stage-planning.md).

| Technology | Status | Track | Bounded evaluation | Guardrail |
| --- | --- | --- | --- | --- |
| [Semantica AGI Context Graph](semantica-context-graph.md) | evaluate / POC | DEV + APP | PROV-O interoperability, developer context projection, bounded graph/GraphRAG/ER/policy benchmarks; verify Apache AGE and pgvector support in the tested build | Derived projection behind project-owned ports/adapters; repository artifacts, source assertions, ER decisions, reconciliation, and canonical state remain authoritative |
