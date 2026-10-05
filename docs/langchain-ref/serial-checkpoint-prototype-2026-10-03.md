# Serial checkpoint prototype observations — 2026-10-03

Selected adapter versions: LangGraph1.2.12, SQLite checkpoint3.1.1, coherent dependency
resolution in `uv.lock`. Base package remains dependency-free. [ADR-030](../adr/030-optional-serial-review-workflow.md)
and [public contract](../product/serial-review-workflow-v1.md) own project decisions.

Useful mechanics verified in local fixture tests:

- `StateGraph(State, context_schema=Invocation)` passes fresh non-checkpoint context into
  nodes. A second process must explicitly supply its authorized context on resume.
- `interrupt({brief_id, digest, snapshot_id})` exposes an immutable reference. The resumed
  node starts again; keep side effects outside the pre-interrupt path.
- `Command(resume=receipt.brief_id)` supplies a continuation value, never permission. Our
  application records the human receipt first and validates scope/digest/version independently.
- `SqliteSaver` plus application-issued `thread_id` survives process exit. Use a separate
  checkpoint database, authorize before loading, and expose no client checkpoint/fork API.
- After durable save and process crash, `graph.invoke(None, config, context=...)` continues
  the pending save node; the application ledger returns its original idempotent result.
- A crash after draft persistence reuses that exact brief. `recover` cannot acquire review
  or action authority. Missing checkpoints remain infrastructure uncertainty.
- Explicit partial updates in a serial graph need no append reducers. No parallel/fan-in
  behavior has been accepted. A cooperative deadline does not hard-cancel synchronous tools.
- LangGraph's outputs/streams are not authorization or redaction boundaries. Our public CLI
  constructs its own allowlisted DTO; browser/event-stream acceptance remains separate.
- `langsmith.tracing_context(enabled=False)` prevents environment-enabled tracing in this
  local prototype. Trace export still requires explicit authorization.

Official references: [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts),
[persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).
These are framework mechanics, not live-model evidence, benchmark quality or a production
workflow adoption decision. No course transcript, credential or proprietary example is stored.
