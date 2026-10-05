# Introduction to LangGraph: patterns for this repository

Reviewed selected notebook code cells and adjacent explanations at
[`fa15bec4`](https://github.com/langchain-ai/langchain-academy/tree/fa15bec4a51c541c40c261586b037c9d134977b1).
This is not a claim to have executed all modules or watched their videos.

## Artifact map

| Notebook | Useful mechanism | Application |
|---|---|---|
| [Agent](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-1/agent.ipynb) | Conditional model/tool loop | #53 routing and bounded tool invocation; services retain calculations |
| [State reducers](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-2/state-reducers.ipynb) | Per-key update semantics and concurrent writes | Explicit channels for result refs, brief identity and execution events |
| [Multiple schemas](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-2/multiple-schemas.ipynb) | Separate input/internal/output views | Public request cannot supply approval or authoritative assessment |
| [Trim/filter messages](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-2/trim-filter-messages.ipynb) | Bound model context independently of stored history | Preserve immutable evidence outside summaries; keep tool-call/result pairs valid |
| [External memory](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-2/chatbot-external-memory.ipynb) | SQLite checkpointer | Local restart demonstration, with fresh process and same durable run identity |
| [Dynamic breakpoints](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-3/dynamic-breakpoints.ipynb) | Conditional interruption; uses older `NodeInterrupt` style | Learn the control-flow idea; use current interrupt API for new work |
| [Time travel](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-3/time-travel.ipynb) | Inspect/fork state history | Debug counterexamples; forked execution must not reuse approval silently |
| [Parallelization](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-4/parallelization.ipynb) | Reducers and explicit multi-predecessor joins | Only parallelize independent reads; test unequal-depth branches |
| [Subgraphs](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-4/sub-graph.ipynb) | Isolated workflow composition | Potential later decomposition; no need for multiple agents in first demo |
| [Memory store](https://github.com/langchain-ai/langchain-academy/blob/fa15bec4a51c541c40c261586b037c9d134977b1/module-5/memory_store.ipynb) | Cross-thread namespaced data | Optional preferences; never overwrite governing procurement facts with a summary |

## State and scheduling

The reducer notebooks demonstrate updates for individual state keys. With list concatenation,
nodes return the new entries, not the accumulated list. Otherwise the shared prefix is duplicated.
Concatenation is not deduplication, audit persistence or ordering by business time.

The parallelization notebook includes an unequal-length branch and an explicit list-valued
predecessor edge. Use that form when the consumer must wait for both named branches. Separate
incoming edges do not express that all-predecessor requirement; equal-depth examples can hide
the difference. Multi-writer keys require suitable reducers; distinct single-writer keys do not
need concatenation just because the nodes run concurrently.

Current [Graph API documentation](https://docs.langchain.com/oss/python/langgraph/graph-api)
confirms per-key reducers and distinguishes state schemas from routing. It also warns that
private state channels can appear in streamed state. Therefore an output schema is not a
redaction boundary. Project proposal: construct an explicit allowlisted public event DTO and
test streams as well as final responses. Validate all model/boundary input; TypedDict alone
does not enforce runtime value validity.

## Pause and resume: use current semantics

The current [interrupt guide](https://docs.langchain.com/oss/python/langgraph/interrupts)
uses `interrupt(payload)` and `Command(resume=value)` with a checkpointer and stable thread ID.
On resume, the interrupted node runs again from its beginning. Put side effects in a later
node or make them idempotent; do not treat code before the interrupt as executed exactly once.
Avoid swallowing the interrupt control exception in a broad catch. Keep interrupt positions
stable within a node and make payloads serializable.

Project proposal: interrupt with a persisted brief reference, digest and evidence-snapshot
identity. The resume endpoint authenticates the reviewer and records a decision bound to those
identities. The graph receives a receipt ID, not trusted client `approved=true`. The save service
revalidates authority, freshness and exact content and commits once using a durable idempotency
key. Editing the brief or forking evidence requires fresh approval. A graph checkpoint cannot
atomically guarantee a separate application's save; test crash-after-save-before-checkpoint.

## Three stores with different purposes

Current [persistence documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
distinguishes thread-scoped checkpoints from cross-thread stores. In-memory savers do not survive
process exit; a local SQLite-backed saver can support a development restart exercise.

For procurement, keep the boundaries explicit:

| Record | Owner | What it proves |
|---|---|---|
| Graph checkpoint | Optional runtime adapter | Where execution can resume |
| Approved brief, decision and idempotency result | Application persistence | What was authorized and saved |
| Source assertions, governing decisions and evidence | Domain/application services | Why the business assessment is justified |

Thread IDs are lookup keys, not authorization tokens. Namespaces organize records; scope checks
must still authorize every read/resume. Never use a module-global active thread for concurrent
requests. A learned preference can affect presentation but cannot supersede approved source data.

## Version and deployment limits

The inspected course requirements include floating packages. Its notebook APIs span older and
newer conventions. Pin a coherent optional dependency set and validate the selected APIs before
integration; a source commit does not pin an environment. New docs also describe newer streaming
and response-schema features that these snippets do not require.

Studio/managed deployment is a debugging or hosting option, not a prerequisite for our existing
HTTP server. Do not copy a deployment example as proof of disconnected operation. Start with one
workflow and a persistent local run store; add distributed workers only for measured needs.
