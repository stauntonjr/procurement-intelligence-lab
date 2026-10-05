# Application approval and LangGraph integration notes — 2026-10-03

Reference refresh for #53/#67/#68, after the application-owned brief/save implementation.
Sources: [official interrupt guide](https://docs.langchain.com/oss/python/langgraph/interrupts),
[StateGraph reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph),
[SQLite checkpointer reference](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver).
The interrupt guide was read directly; reference search snippets identify the latter APIs.
These notes are design input, not executed graph or live-model evidence.

The guide confirms durable checkpoints plus the same thread identity support review resume.
The interrupted node restarts, so it must not draft another brief or perform a save before its
interrupt. Use separate draft, review-interrupt and save nodes. Typed interrupt responses are
version-dependent; the current guide requires langgraph>=1.2.12 for response_schema. Regardless
of framework validation, the application must validate the exact receipt and current evidence.

Repository application of the pattern:

```python
# Schematic, not an implemented adapter.
run = authorized_run_service.resume(run_id, context=server_context)
# Supply only this application-owned thread_id; expose no checkpoint-fork arguments.
config = {"configurable": {"thread_id": run.thread_id}}
# Draft once in its own node. Review node exposes brief_id/digest and pauses.
# Resume authenticates separately; a Command payload supplies a decision, never permission.
# Save node invokes BriefReviewService.save; checkpoint state cannot grant approval.
```

Keep actor/context injection outside persisted graph state. Reload and compare the complete run
binding before checkpoint reads. Resume uses the persisted brief ID/digest; edited content creates
a new active version and a new review. A crash after durable save replays to the same saved result.
Expose allowlisted application events rather than raw graph state or model reasoning. Test process
restart, stale/forked state, corrupt bindings, expiry during lock contention and duplicate resume.
