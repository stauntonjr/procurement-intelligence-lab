# Open questions and hypotheses

These are benchmarkable hypotheses, not locked commitments. Decisions require representative synthetic benchmarks, cost/latency measurements, evidence-quality review, and comparison with the simplest repository-native alternative.

Current open questions include:

- Postgres JSONB versus normalized tables for early document structure
- pgvector versus a separate vector service
- graph projection shape and whether higher-order/hypergraph context earns specialized infrastructure
- extraction model selection
- ER candidate generation, scoring, contextual evidence, and thresholds
- OTel/Logfire deployment
- UI framework
- durable backend orchestration choice (for example Temporal versus cloud-native alternatives)
- Pydantic AI or another typed agent/tool boundary
- FastMCP as an external interoperability adapter

## LM and agent framework hypotheses

### DSPy

**Status:** evaluate relatively early once a representative labeled corpus exists.

**Hypothesis:** metric-driven LM-program optimization may improve schema mapping, query-intent planning, or evidence-grounded synthesis over hand-authored prompts while keeping production runtime simple and typed.

**Adoption evidence required:** repository-owned eval improvement, reproducible artifacts, error analysis, and no unacceptable runtime/framework coupling.

### LangGraph

**Status:** deferred to the operational-agent milestone.

**Hypothesis:** LangGraph may earn a runtime role for genuinely stateful, branching, resumable, human-in-the-loop operational-agent workflows.

**Adoption evidence required:** a real workflow whose persistence, pause/resume, branching, or human-approval needs are materially clearer or safer than a small repository-native state machine. It is not a document-processing or deterministic-workflow framework by default.

### LangChain

**Status:** no planned foundational adoption.

**Hypothesis:** individual LangChain integrations may reduce implementation or maintenance cost for a concrete adapter.

**Adoption evidence required:** a specific component solves a concrete problem while repository-owned domain/application types remain authoritative and replaceable.

See `docs/architecture/agent-framework-evaluation.md` for the full evaluation policy and the distinction between durable backend workflows and stateful agent runtimes.
