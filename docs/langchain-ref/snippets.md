# Adapted snippets

These are original project-oriented sketches informed by the linked course code and current
docs. They are not production implementations. Only the stdlib evaluator example is executed
in this reference slice; LangGraph code is syntax-checked, not runtime-qualified.

## Partial updates and an explicit join

Source: [state reducers and parallelization](langgraph-patterns.md#state-and-scheduling).
This sketch collects candidate IDs, not governing evidence. Duplicate removal and evidence
qualification belong to the downstream application service.

```python
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class SearchState(TypedDict):
    candidate_ids: Annotated[list[str], add]
    complete: bool


def exact_candidates(state: SearchState) -> dict:
    return {"candidate_ids": ["synthetic:exact-1"]}


def description_candidates(state: SearchState) -> dict:
    return {"candidate_ids": ["synthetic:description-1"]}


def join_candidates(state: SearchState) -> dict:
    return {"complete": True}  # Search branches finished; coverage is NOT established.


builder = StateGraph(SearchState)
builder.add_node("exact", exact_candidates)
builder.add_node("description", description_candidates)
builder.add_node("joined", join_candidates)
builder.add_edge(START, "exact")
builder.add_edge(START, "description")
builder.add_edge(["exact", "description"], "joined")
builder.add_edge("joined", END)
graph = builder.compile()
```

Future runtime check: insert an extra node into one branch and assert the join runs once after
both finish. Do not infer result ordering from the concatenation reducer.

## Interrupt with a review receipt, not a client approval flag

Source: [current interrupt semantics](https://docs.langchain.com/oss/python/langgraph/interrupts).
The following adapter fragment presumes an already-persisted immutable brief. It does not
implement authentication, receipt validation, expiry, or a save transaction.

```python
from typing import TypedDict

from langgraph.types import Command, interrupt


class ReviewState(TypedDict):
    brief_id: str
    brief_digest: str
    evidence_snapshot_id: str


def await_review(state: ReviewState) -> dict:
    receipt_id = interrupt({
        "kind": "review_brief",
        "brief_id": state["brief_id"],
        "brief_digest": state["brief_digest"],
        "evidence_snapshot_id": state["evidence_snapshot_id"],
    })
    if not isinstance(receipt_id, str) or not receipt_id:
        raise ValueError("a persisted review receipt ID is required")
    return {"review_receipt_id": receipt_id}


def resume_with_receipt(graph, server_bound_run_id: str, receipt_id: str):
    # Caller must authenticate and authorize this run and receipt before invoking.
    return graph.invoke(
        Command(resume=receipt_id),
        config={"configurable": {"thread_id": server_bound_run_id}},
    )
```

The full graph's internal schema must include `review_receipt_id`. A separate save node calls
the application's exact-brief approval/idempotency service; it cannot save merely because the
receipt string exists. Use a durable checkpointer and test a fresh-process restart, rejected
receipt, wrong scope, changed snapshot and crash between durable save and checkpoint update.

## Code-based trajectory gate, without external dependencies

[trajectory_gate.py](examples/trajectory_gate.py) is a small executable illustration of how to
adapt the course's tool-order evaluator. It differentiates pass, fail, unknown and not-applicable;
requires successful inspection; binds approval/save to the same brief and snapshot; and detects
duplicate save events. It is deliberately a trace-consistency check, not an authorization engine
or proof that the trace is complete/authentic.

Run from the repository root:

```sh
python3 docs/langchain-ref/examples/trajectory_gate.py
```

For actual acceptance, reconcile event completeness with the durable application store, identify
event retries by stable IDs, validate reviewer permissions/expiry, and inspect stored result count.
Concurrent paths require causal identifiers rather than assuming list order proves causality.

## Reproducible experiment record

Use [experiment-template.json](experiment-template.json) as a field checklist, not an evaluation
result or official repository schema. Nulls explicitly mean unmeasured/not yet selected. It
separates dataset/model/code identity, live versus fixture execution, independent metric values,
unknown/failed counts and optional trace URLs. Map the final implementation to existing semantic
evidence records instead of introducing a second completion authority.
