# Agent and LM framework evaluation

## Principle

Frameworks do not define the architecture. They may implement bounded mechanics behind repository-owned ports and contracts when they demonstrate measurable value.

The project currently treats LangGraph, LangChain, and DSPy as distinct candidates for distinct problems rather than as a single "LLM stack."

## Current stance

| Technology | Candidate role | Current status |
| --- | --- | --- |
| DSPy | Development-time optimization of LM programs against explicit eval metrics | Evaluate relatively early |
| LangGraph | Runtime for genuinely stateful, branching, resumable, human-in-the-loop operational agents | Defer to agent milestone; prototype before adoption |
| LangChain | Optional integration convenience for specific providers/tools | No planned architectural adoption |
| Pydantic AI | Typed runtime agent/tool boundary | Candidate, benchmark with alternatives |
| FastMCP | External agent/tool interoperability | Candidate interface adapter |
| Temporal / durable workflow engine | Reliable deterministic backend workflows | Separate concern from agent runtime |

## DSPy

DSPy is most interesting as part of the development and evaluation plane, not as the application's system of record or orchestration runtime.

Candidate uses include:

- schema mapping from `StructuredDocument` to domain fields
- ambiguous attribute extraction from descriptions
- query-intent/tool-selection programs
- evidence-grounded answer synthesis
- abstention and clarification behavior

A DSPy experiment must optimize against a repository-owned metric and golden corpus. Examples include field F1, tool-selection accuracy, claim support, citation accuracy, or abstention correctness.

The desired pattern is:

```text
golden corpus
    -> candidate LM program
    -> optimization / experiment
    -> repository evals
    -> baseline comparison
    -> versioned artifact
    -> PR evidence
```

DSPy optimization should not silently modify production behavior. Optimized instructions/examples/configuration must be versioned and promoted through the same review and evaluation gates as other intelligence changes.

Production runtime may remain a simple typed LLM adapter even when DSPy is used to produce or tune the runtime artifact.

## LangGraph

LangGraph should be considered only when an operational agent workflow has requirements such as:

- persistent state across multiple reasoning/tool steps
- non-trivial branching chosen at runtime
- pause/resume around human approval
- resumability after process failure
- streaming or incremental user interaction
- long-running investigation state

A representative future workflow might be:

```text
revision mismatch detected
    -> collect evidence
    -> resolve ambiguity
    -> assess impact
    -> draft remediation
    -> wait for human approval
    -> execute approved action
    -> audit result
```

LangGraph should not be used merely to draw a pipeline as nodes. Predetermined processing such as document structuring, schema mapping, normalization, persistence, entity-resolution stages, or reconciliation remains ordinary application/workflow code.

If adopted, LangGraph must sit behind a repository-owned abstraction such as `AgentWorkflowRuntime`. Framework-specific state must not become canonical procurement state.

### Architectural invariant

> Agent-framework state is execution state, not business truth.

Assertions, entity-resolution decisions, reconciliation, operational state, anomalies, predictions, decisions, actions, and audit records remain in the canonical application/data model.

## LangChain

LangChain is not planned as a foundational dependency. It may be introduced behind an adapter when a specific integration materially reduces maintenance or implementation cost.

Adoption criteria:

- the integration solves a concrete repository problem
- repository domain/application types remain authoritative
- LangChain document/retriever/tool/agent types do not leak into core contracts
- the adapter can be replaced without rewriting business logic
- tests demonstrate equivalent behavior through the repository-owned port

The preferred posture is "implementation utility when earned," not "application framework."

## Temporal versus LangGraph

These solve different classes of problems and should not be conflated.

```text
Temporal / durable workflow
"What backend work must reliably happen?"

LangGraph / agent runtime
"How should an LLM-driven agent dynamically reason, branch,
pause, resume, and choose tools?"
```

For example, document ingestion and reprocessing are durable backend workflows even if they contain no LLM reasoning. A procurement investigation agent may require stateful LLM-driven branching without owning the ingestion workflow.

## Evaluation requirements

No framework is adopted because it is popular or because a demo is concise. A candidate implementation should be compared with the simplest repository-native alternative.

Framework evaluations should consider, as applicable:

- task quality / eval metric delta
- latency and throughput
- token and provider cost
- persistence/resume semantics
- failure recovery
- observability and traceability
- human-approval ergonomics
- testability
- dependency weight and transitive risk
- framework-type leakage into domain/application layers
- ability to reproduce behavior across versions
- operational complexity

## Planned experiments

### DSPy

Evaluate when the project has a representative labeled corpus for a prompt/program-dependent task. Early candidates are schema mapping and query intent planning.

Question:

> Can metric-driven LM-program optimization outperform a hand-authored baseline on repository-owned evals without increasing runtime coupling?

### LangGraph

Evaluate during the operational-agent milestone after deterministic tools and approval/audit services exist.

Question:

> Does a real agent workflow require state, branching, pause/resume, and human interaction complex enough that LangGraph is materially clearer or safer than a small repository-native state machine?

### LangChain

No generic evaluation is planned. Evaluate only in response to a concrete integration need.

Question:

> Does this specific LangChain component materially reduce adapter implementation or maintenance cost while preserving repository-owned contracts?

## Development-agent integration

LM-program optimization should eventually become a repeatable development skill. A development agent claiming to improve a prompt or LM program must provide evidence analogous to a model change:

1. identify the target metric and baseline
2. run the common golden corpus
3. record candidate configuration/program version
4. compare metrics and error cases
5. preserve reproducible artifacts
6. document regressions and tradeoffs
7. promote only through review

"Improved the prompt" is not an acceptable completion claim without evaluation evidence.
