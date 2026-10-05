# Building Reliable Agents: useful artifacts and limits

Source prefix for all repository links below:
[official Python materials, pinned revision](https://github.com/langchain-ai/lca-reliable-agents/tree/8fe1c139767fa6efc32e9b21230cff8f45932356/python).
These observations concern inspected code, not inaccessible lesson videos.

## Artifact map

| Artifact | What was learned | Procurement application |
|---|---|---|
| [Baseline and instrumented agents](https://github.com/langchain-ai/lca-reliable-agents/tree/8fe1c139767fa6efc32e9b21230cff8f45932356/python/officeflow-agent) (`agent_v0.py` → `agent_v1.py`) | Provider wrapping and tool spans add observability without requiring a graph rewrite | Instrument the model/tool adapters; keep domain services independent, #75 |
| [Thread example](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-1/lesson-2/thread_agent.py) | Conversation identity groups related interactions | Server binds run/thread to scope; use fresh run state per independent evaluation, #68/#72 |
| [First experiment](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-3/run_experiment.py) | A target, dataset and evaluators form an experiment | Wrap the actual HTTP/agent entry point, not a helper returning the expected answer |
| [Schema-before-query evaluator](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-4/eval_schema_check.py) | Evaluate intermediate tool order, not just final prose | Check scope validation → successful inspection → exact-brief approval → one save |
| [Evaluator runner](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-4/run_eval.py) | Each dataset example should start a fresh conversation | Pass IDs explicitly; do not mutate a module-global thread ID under concurrent evaluation |
| [LLM-judge runner](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-5/run_experiment.py) | A dataset can carry remotely configured evaluators | Export/pin judge rubric and evaluator version; a UI-only setting is insufficient reproducibility |
| [Pairwise experiment](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-6/run_pairwise_experiment.py) and [judge](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-2/lesson-6/eval_conciseness_pairwise.py) | Compare two versions on common inputs and randomize presentation order | Judge brief clarity only after factual/policy gates; report ties, errors and order sensitivity |
| [Whole-document retrieval](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/officeflow-agent/agent_v4.py) | Retrieval-unit size is a variable worth testing | Compare row, section and document context under #55/#62; no assumption that no-chunking wins |
| [Synthetic trace generator](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-3/lesson-2/generate_traces.py) and [uploader](https://github.com/langchain-ai/lca-reliable-agents/blob/8fe1c139767fa6efc32e9b21230cff8f45932356/python/module-3/lesson-2/upload_traces.py) | Synthetic traces can populate a teaching/analysis exercise | Useful as labeled observability fixtures only; never acceptance or production measurements |

## Important adaptations from inspected code

**A trace of a request is not proof of successful execution.** The schema-order evaluator reads
tool-call arguments from message history and gives a passing score when there are no database
calls. That is reasonable for its narrow exercise but cannot establish successful scoped
inspection here. Track invocation, successful result, typed failure, and applicability separately.
A required investigation with missing events is `unknown`, not pass; an explicitly out-of-scope
case is `not_applicable`, not an extra correct example in the success denominator.

**Conversation isolation must be explicit.** The inspected agents keep history in module-level
dictionaries and identify the active conversation with module globals. One runner resets that
global, while other wrappers call `chat()` directly. This is a leakage/concurrency risk to test,
not a measured failure of a deployed system. Construct request-scoped invocations and reject
cross-project resumes. Clear model history between independent benchmark examples.

**Do not copy the generic SQL tool.** OfficeFlow's tool takes SQL text, executes it using SQLite,
and returns errors as text. Our agent should call approved typed application services. Tool
descriptions help model routing; executable authorization and typed results enforce the contract.
Bound loop steps, model calls and elapsed time; the inspected `while response_message.tool_calls`
loop itself supplies no explicit step budget.

**Evaluate retrieval changes rather than inheriting them.** Whole-document context can retain
qualifications lost by chunking, but can also increase distraction and token cost. The inspected
cache checks file modification times; our projection identity must include source hashes,
document removal/addition, model and config changes. Retrieval candidates cannot establish
document authority, complete order coverage or canonical identity.

**Keep trace provenance truthful.** The uploader remaps IDs and shifts synthetic timestamps to
make traces appear recent. Do not copy that behavior into evidence collection. If replaying a
fixture for UI testing, retain original timestamps, record replay time separately, and label
`execution_kind=synthetic_fixture`. Never include those rows in live latency or model-quality
aggregates. The current application plan already distinguishes recorded fallback from inference.

## Evaluation recipe for this project

The [current evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
separate application inputs from evaluator references and distinguish dataset experiments from
online run monitoring. Use that separation for the corpus plan: input-only target, external gold,
versioned results. Promote observed failures into reviewed regression examples; online feedback
alone does not supply ground truth.

Our proposed scorecard has independent columns: authoritative value/status agreement, complete
evidence roles, source resolution, safe tool trajectory, appropriate abstention, explanation
support, latency/calls and errors. A concise wrong answer fails. LLM judges may assist explanation
review after calibration against human judgments; they never override deterministic semantics.
Keep category/project denominators, failed runs and withheld labels explicit. Do not infer corpus
sufficiency from the small example dataset included with a teaching course.

## Observability recipe

[LangSmith observability](https://docs.langchain.com/langsmith/observability-concepts) supports
manual instrumentation and metadata in addition to provider integrations. Instrument at the
adapter boundary; this does not require adopting LangChain's application abstractions.

Project proposal: correlate application run ID, graph thread/checkpoint ID, query ID, corpus
manifest hash, application revision, model identity, prompt/tool-schema version and evidence
snapshot. Capture tool start/result/error and bounded counters. Exclude credentials and hidden
reasoning; allowlist exported fields. Application persistence owns approval and saved briefs.
LangSmith remains optional under #75, with local audit records available when tracing is disabled.
