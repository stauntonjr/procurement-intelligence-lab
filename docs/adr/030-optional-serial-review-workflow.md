# ADR-030: Optional serial review checkpoint adapter

Status: accepted for a fixture-only prototype on the implementation branch.
Primary #53; part of #68/#70. Builds on ADR-028 and ADR-029.

The approved interview-demo plan needs durable pause/resume around exact human review.
Use an optional, pinned LangGraph/SQLite checkpointer adapter behind a repository-owned
`AgentWorkflowRuntime` Protocol. Compare its behavior with the existing deterministic
brief CLI through the same application services; do not adopt framework state as business
truth or replace deterministic calculations.

Start with a typed fixture request, draft, review interrupt and save. No model, free-text
answer synthesis, tool-selection quality, browser authentication or live acceptance is
claimed. The graph is a persistence prototype for the future interpreted workflow.

The adapter derives thread identity from an authorized, version-bound application run
before loading checkpoints. It accepts no caller-supplied checkpoint ID, state or approval
boolean. Trusted invocation context is supplied separately, never serialized. Human review
is recorded by the application before resume; saved-result authority remains in its ledger.
Graph recovery reuses a persisted draft and acknowledges the one durable saved result.

Serial invocations use a bounded SQLite coordinator separate from checkpoint and application
databases. Explicit partial updates avoid reducers. A recursion ceiling and cooperative
deadline check bound orchestration; synchronous calls are not hard-cancelled. Read failures
are not automatically retried in this first prototype. Optional dependencies and their
transitive lock remain separate from dependency-free base installation.

The cost is additional execution storage and transitive dependencies. Adoption for live
inference still requires configured-model acceptance, bounded model/tool behavior and a
deliberate framework comparison. Local restart/recovery evidence alone cannot satisfy it.
