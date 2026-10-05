# Applying the course patterns to the accepted project boundaries

This checklist informs implementation; it does not change Issue status or authorize model
execution, telemetry upload, infrastructure provisioning, or external actions.

| Work item | Concrete reuse | Acceptance evidence |
|---|---|---|
| #66 typed tools | Explicit inputs/outputs and observable invocation | Tool output equals direct scoped service output; model cannot grant scope |
| #53 orchestration | Single conditional workflow with partial state updates | Unsupported request, malformed output, tool exhaustion and clarification handled visibly |
| #67 review | Dynamic interrupt around a persisted brief | Exact brief/snapshot binding; forged, stale and cross-run decisions rejected |
| #68 recovery | Persistent checkpoint plus application-owned result | Restart while paused; crash after save; retry produces one durable brief |
| #70 reproducibility | Experiment/run metadata | Model, prompt, tool schema, source hashes and tested application revision retained |
| #72 evaluation | Code-based tool trajectory plus result/evidence checks | Missing trace does not pass; all failed runs remain in denominators |
| #75 tracing | Optional adapter instrumentation | Trace-disabled workflow still works; exports exclude secrets and hidden reasoning |
| #62 corpus/retrieval | Versioned dataset and comparable target experiments | Project-held-out queries; gold unavailable to runtime; quality separate from load testing |
| #74 walkthrough | Public execution events distinct from domain evidence | View source, uncertainty and recovery through real UI; no simulated-success timeline |

## Priority and integration seams

1. Implement scoped deterministic investigation and source inspection from the
   [corpus plan](../superpowers/plans/2026-10-03-procurement-demo-corpus.md), Tasks 1–4.
2. Wire those services into #66/#53. Keep one runtime owner of active run/thread identity.
3. Build #67/#68 as one coherent application-authority and persistence slice. Reuse interrupt
   mechanics, not the toy approval semantics of a tutorial.
4. Make trajectory/result/evidence evaluators part of #72 and corpus Task 5 from the outset.
5. Add optional LangSmith export last, within #75's existing time box. Use real measured events.

## Specific tests worth carrying into implementation

- Parallel branches return deltas; a longer branch delays the single explicit join.
- An output/private schema does not accidentally expose state through streamed events.
- A new evaluation example gets a new isolated thread; retries of that example preserve
  intended run identity without inheriting another query's history.
- A read tool that errors cannot satisfy the successful-inspection prerequisite.
- An empty or partial trace is unknown; absence of required tools is not success.
- A valid source ID attached to an unsupported statement fails explanation-support evaluation.
- Modified brief/evidence invalidates previous approval, including after a checkpoint fork.
- Resume rejects unauthorized run IDs before state loading; repeated save is idempotent.
- A model timeout or trace exporter failure cannot fabricate a completed investigation.
- Derived summary/memory cannot change the authoritative procurement status or quantity.
- Fixture/replay traces are excluded from live latency and model-quality reports.
- A retrieval-cache source deletion or model/config change invalidates the projection identity.

## Deferred patterns

Multi-agent research assistants, cross-thread learned memory, managed deployment, LLM judges,
online automation and prompt optimization are useful course topics but not requirements for the
first release. In particular, the three-store distinction in the notes supports durable recovery;
it is not a plan to learn new procurement facts from chat history.
