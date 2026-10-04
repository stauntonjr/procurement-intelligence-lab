# ADR-032: Local model intent with an application-owned inference journal

Status: Accepted for the authorized demo branch; not merged to main.
Date: 2026-10-03. Primary #53; governing #66/#67/#68/#70/#71/#72. Builds on ADR-028/029/030/031.

## Context and decision

The user selected the already-loaded Qwen 3.6 model. The DGX model endpoint identifies
`nvidia/Qwen3.6-35B-A3B-NVFP4`; `/version` identifies
`0.23.1rc1.dev1353+g81f51a780.d20260721`. Reuse that process without provisioning or reloading.

A framework-independent QuestionInterpreter port returns only ephemeral content and token usage.
The stdlib local-vLLM adapter uses numeric loopback HTTP, ignores proxies, refuses redirects,
requests a strict JSON schema, disables thinking, and limits output to 256 tokens. Temperature is
0; transport socket timeout is 30 seconds; one attempt, no automatic inference retry. The socket
inactivity timeout is not a hard wall-clock cancellation or proof that server-side GPU work stopped.

An application-owned literal catalog matcher supplies exact item mentions to the model and validates
that investigation has one matching canonical mention. It escapes identifiers, preserves multiple
mentions and rejects prefix/alias guesses; it supplies no quantities, case IDs or gold. This feature
was added after a retained development repetition falsely requested item clarification.

Application validation binds the proposal to the explicit human-selected project, aware as-of and
scoped admitted catalog. Clarification/unsupported/invalid proposals cannot invoke investigation.
The model cannot supply quantities, evidence, permissions, reviewer receipts or SQL. The existing
services construct the canonical brief and enforce review/save. This is bounded intent routing,
not model-generated factual synthesis or fuzzy retrieval.

The application creates one immutable LIVE run before inference. An independent durable journal
stores the question hash, caller as-of, accepted item or closed abstention/failure reason, measured
elapsed time and reported tokens (unknown on failure when unavailable). No raw response, prompt,
hidden reasoning or trace export is retained. A pending attempt after a crash stays unknown and
never automatically reissues inference. Existing tool-event vocabulary stays unchanged.

AgentWorkflowRuntime.begin accepts an existing owned/version-compatible run. It creates or
recovers the serial checkpoint for that exact item/date, refusing a changed request. A durable
accepted interpretation can survive a crash before checkpoint creation. Status is read-only;
explicit recovery resumes work without recalling the model. SQLite and LangGraph remain mechanics
behind ports. The human CLI and authenticated loopback HTTP routes compose the same services.

## Consequences and acceptance limits

The journal introduces a separate storage contract, while preserving tool-event semantics and
application-owned human authority. Prompt/schema/endpoint/budgets/framework versions, corpus and
application bytes bind immutable run versions. Version mismatch refuses recovery.

Explicit date/project remain user controls. The 2026-10-04 development clarification defines
requirement governance/conflict and document approval applicability as read-only review intents.
A document-relative predicate (for example, before document approval) describes evidence at the
selected cutoff; it is not human approval to save or a request for an inferred instant. Calendar
boundary wording can use the supplied cutoff only when consistent with it. Different explicit
dates, inconsistent boundaries, unresolved relative query cutoffs and ambiguous items require
clarification. The model never calculates a replacement cutoff; deterministic policies still decide
applicability and quantities. This clarifies the existing intent prompt, not governing policy. Broad natural-language quality, original tiny fixture routing, hard cancellation,
remote providers, streaming, public deployment and browser accessibility remain separate acceptance.
Nine repeated live corpus walkthroughs are bounded smoke evidence, not held-out accuracy.

Protocol sources: [vLLM structured outputs](https://docs.vllm.ai/en/stable/examples/features/structured_outputs/)
and [Qwen vLLM deployment](https://qwen.readthedocs.io/en/stable/deployment/vllm.html), consulted
2026-10-03; actual loaded endpoint behavior takes precedence over documentation assumptions.
