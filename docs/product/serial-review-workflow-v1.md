# Fixture serial review workflow v1

Primary M5 / #53; part of #68/#70. ADR-030 extends ADR-028/029 for Task 5B of the
approved interview-demo plan. This is an optional persistence prototype, not live inference.

- Authoritative inputs: authorized immutable application run/configuration, typed item/date,
  admitted synthetic corpus and actual audited tool results, exact brief and human receipt.
- Authoritative output: exact deterministic brief and, after valid approval, one durable
  application saved result. Checkpoints describe execution only.
- Scope and as-of: initiating principal, tenant/project/site and aware request time; threads
  derive only from owned runs. Permission/configuration checks precede checkpoint loading.
- Governing policy: READ_STATE/READ_EVIDENCE for runtime; REVIEW and ACT remain on the
  separate human invocation. Exact active version, digest, evidence freshness, receipt lease
  and issued idempotency key retain ADR-029 policy. No client approval/state/fork inputs.
- Evidence retained: run versions, tool start/success/failure, source snapshots, immutable
  brief/digest, durable receipt/result, local SQLite checkpoints and process-recovery tests.
- Typed failures: input/scope/configuration and approval conflicts retain their existing
  codes; workflow storage/integrity failures are infrastructure; budget exhaustion is policy.

The graph is serial: draft -> review interrupt -> optional save -> completion. The draft node
reuses the matching durable draft after a crash. The review node has no pre-interrupt effects.
The human boundary first records the exact decision; an invocation-local receipt enables
resume. Context/permissions never enter the checkpoint. A crash after save repeats the
idempotent application save and returns its original result. Status reads the application
result/receipt ledger, so checkpoint completion cannot fabricate success or rejection.

At most eight graph steps per invocation, one read attempt and a 30-second cooperative
deadline checked between nodes. Local invocations serialize with a five-second maximum
coordinator-lock wait. Synchronous calls cannot be safely hard-cancelled; time in a blocked
call may exceed the cooperative deadline. No retry, streaming, parallel execution, inference,
trace upload, arbitrary SQL tool, external procurement action or production login is provided.
Environment-enabled LangSmith tracing is explicitly disabled within this adapter.

`langgraph==1.2.12` and `langgraph-checkpoint-sqlite==3.1.1` resolve together, with transitive
dependencies pinned in `uv.lock`. Base installs remain dependency-free. The fixture CLI uses
`provider=fixture`, `model=none`, version-bound graph/tools/manifest, and a SHA-256 application
source fingerprint. Runtime/version drift rejects old resumes. Freeze code while rehearsing;
this strict prototype has no checkpoint migration policy.

```sh
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.workflow \
  --database /tmp/procurement-review.db start --project atlas \
  --item GPU-A --as-of 2026-10-01T00:00:00Z
```

Use returned run/brief IDs and digest with `status --run-id ...` or
`review --run-id ... --brief-id ... --digest ... --decision approve|reject`, with the same
database/project flags. `recover --run-id ...` recovers a known run interrupted during draft,
without authority to save. If start crashes before returning its run ID, a maintainer must
inspect the local run ledger; a browser run-list/recovery affordance remains future work.
CLI stdout is an explicit allowlist, not a raw graph stream. Browser/stream redaction acceptance
remains open along with natural-language interpretation and live-model evaluation.

Sources informing mechanics: [interrupt semantics](https://docs.langchain.com/oss/python/langgraph/interrupts),
[durable persistence](https://docs.langchain.com/oss/python/langgraph/persistence).
