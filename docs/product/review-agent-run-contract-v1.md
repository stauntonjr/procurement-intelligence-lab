# Review-agent run contract v1

Primary #70; related #53/#66/#67/#68/#72. Governing ADRs: 009, 014, 019, 028.

## Identity and authority

The application issues opaque run, query, attempt and graph-thread IDs. Every new example gets
new IDs even if its request is identical. A retry/resume retains those bound IDs. Runs bind the
initiating principal and tenant/project/site. The service requires READ_STATE before the store
looks up state with all four authority fields; absent and unauthorized IDs return not-found.
Thread IDs are server-owned correlation, never bearer credentials. Resume rejects any configured provider/model/prompt/tool/fixture/application version or execution-kind change.
A new configuration requires a new run; it cannot write into a previously live or fixture ledger.

Version metadata contains provider, model, prompt, tool schema, fixture and application revisions.
Execution kind is live, fixture or replay and is fixed by the composition root. CLI foundation
runs are fixture records. A version or execution-kind change creates a new run.

## Event allowlist

Each event retains event/run/query/attempt IDs, UTC observed timestamp, kind, causal parent,
tool name/version, evidence-snapshot ID and typed error code where applicable. Permitted kinds
are run_started, tool_started, tool_succeeded, tool_failed and run_completed. Tool completion
references exactly one matching start event. No event accepts arbitrary payloads, prompts,
model content, hidden reasoning, credentials, document text or evaluator labels.

The application records invocation start and actual result/error, not a model's claimed tool
call. Tool/result lifecycle events cannot cross a run/attempt. Exact duplicate event replay is
idempotent; changed content at an existing event ID conflicts. Timestamps cannot precede the
run or causal parent. Public/export serialization uses the same explicit catalog.

The trajectory evaluator requires positive successful results for each expected tool and a
terminal run event. Missing/partial or causally incomplete records are unknown. Explicit errors,
conflicting replays, foreign events or fabricated completion fail. It counts actual starts and
reports event completeness independently of downstream quantity/explanation correctness.
Fixture/replay outcomes are retained but excluded from live aggregates. A non-applicable
example must have an explicit rationale; absence of events cannot imply non-applicability.

## Review/save contract for subsequent slices

A persisted immutable brief binds run/query/attempt, authorized scope, brief ID/version/digest,
evidence snapshot, version metadata and save idempotency key. A review receipt binds the exact
brief, scope, authenticated reviewer, decision and expiry. Resume checks scope before graph
checkpoint loading; save rechecks receipt, current evidence, digest and expiry.
Changing content/evidence invalidates previous approval. A checkpoint fork cannot inherit save
authority. Approval does not change procurement status or reconcile conflicts. A crash after
save but before checkpoint completion must replay to the same single durable saved result.
These review/save behaviors are contracts to implement, not capabilities of this foundation.

## Public foundation caller

`python -m procurement_intelligence_lab.interfaces.agent_runs --database PATH create --project atlas`
creates a fixture run. `... resume --project atlas --run-id ID` resumes that owned record in a
new process. Atlas, Borealis, Cinder and Delta are the configured demo scopes; unknown projects
are forbidden. Output is an allowlisted run DTO. Validation, not-found and infrastructure failures
have explicit codes and nonzero exit status. No credentials or model execution are required.


Foundation failures use the repository typed categories/codes:
`pil.input.agent_run_not_found`, `pil.policy.agent_run_conflict`, and
`pil.infrastructure.agent_run_store_unavailable`. The CLI preserves these stable codes and their categories in explicit JSON failure envelopes. Every identity field is a
bounded nonempty string, timestamp is aware, and event/execution kinds must be supported enums.
Arbitrary objects fail before any event append or DTO export.
The corpus tools extend the closed failure-event catalog with `corpus_admission_failed` for
non-retryable authoritative-source integrity failures. This retains infrastructure semantics.

The `codex/exact-brief-approval` continuation implements the bounded application review/save
contract through a separate local human CLI; see [exact-brief review v1](exact-brief-review-v1.md)
and ADR-029. Graph checkpoints, browser authentication and live model behavior remain subsequent
work. The foundation branch alone does not expose these added capabilities.

## Integration review correction

The run, brief and workflow composition roots identify installed application Python paths/bytes
with a shared SHA-256 fingerprint; package version alone cannot authorize resume. Completion
must follow every recorded timestamp and close the recorded causal path. A non-applicability
rationale cannot erase recorded failures or partial tool execution. See the [integration correction](../project/demo-integration-review-fixes.md).
