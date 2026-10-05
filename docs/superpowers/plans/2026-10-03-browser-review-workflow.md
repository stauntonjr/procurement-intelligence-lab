# Browser review over the fixture workflow

Execute the approved corpus plan Task 5B/5C browser subset inline. Spec:
`docs/superpowers/specs/2026-10-03-procurement-demo-corpus-design.md`.
Primary #74; part of #53/#67/#68/#70. Base 4247519; no merge or deployment.

## Contract
Authoritative inputs: admitted synthetic corpus, immutable application runs/briefs,
review receipts/saved results, and server configured reviewer identity and permissions.
Output: exact review view, bounded owned run discovery, actual application audit events,
scoped source cells, approved/rejected workflow state and one durable saved brief.
Scope/as-of: fixed configured synthetic project, tenant/site/owner; typed aware cutoff.
Policy: ADR-019/028/029/030; authentication precedes application/storage access;
review requires exact displayed ID/digest and application-owned receipt; save revalidates.
Evidence: exact canonical content, versions, evidence refs, digest, audit timestamps,
review/save identities; never checkpoint dictionaries, credentials or hidden reasoning.
Failures: closed authorization/input/policy/infrastructure envelopes, safe UI retry.

## Global constraints
Fixture only. No provider/model selection or inference, public hosting, production auth,
external actions, source corrections, streaming or model-quality claim. Domain unchanged.
Use token file supplied by local operator (private regular file, >=32 characters), only
loopback listener, same-origin bearer headers held in page memory, server-owned context.
History is newest 50 scoped application records; incompatible versions discoverable but
cannot resume. Timeline is fetched persisted application events, not framework streaming.

## Task 1: scoped run discovery and composition
Interfaces: RunStore.recent(context, limit) -> tuple[AgentRun,...]; service permission gate;
shared composition bundle runtime/runs/reader, existing compose return unchanged.
- Write owned, foreign scope, limit and stable newest-order tests first.
- Run `.venv/bin/python -m pytest -q tests/unit/test_agent_runs.py`.
  Expected: new discovery tests fail before implementation and pass after.
- Implement scoped SQL before decode, bound 1..50; expose no checkpoint loading.

## Task 2: authenticated HTTP and browser controls
Interfaces: separate `interfaces.review_web` server; bearer authentication, strict route
schemas, source membership, application event allowlist; shipped inline HTML form.
- Write real HTTP tests first for missing/wrong token, foreign origin/host, malformed/extra
fields, start/review/reject/recovery, exact binding, scoped source/timeline and discovery.
- Run `.venv/bin/python -m pytest -q tests/integration/test_review_web.py`.
  Expected: missing module fails first; implementations then semantic assertions pass.
- Add visible fixture badge, request controls, history/recover, exact facts and source
cells, approve/reject, idempotent acknowledgment; clear stale view on new selection,
disable concurrent submission, preserve useful historical view on recovery failure.
- Test real process restart and installed wheel HTTP caller; run actual browser if available.

## Task 3: verify and close out
- Run `UV_CACHE_DIR=/tmp/pil-uv-cache make check`, `make package-smoke`, `make challenges`.
  Expected: all deterministic checks and known-bad challenge rejection pass.
- One independent whole-slice review; grade findings, one RED/GREEN fix pass if needed.
- Record current-head semantic JSON/PR, handoff/milestone/README and live Project state.
  Keep broader Issues open; no deployed or live inference acceptance claims.

## Review focus
Authentication before storage/checkpoint loading; bearer leakage; browser stale-response
races; changed evidence after display; run owner/version isolation; source membership;
repeated review/save and rejection; malformed/body-size inputs; fixture/live separation.
