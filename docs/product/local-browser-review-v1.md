# Local fixture browser review v1

Primary #74; part of #53/#67/#68/#70. ADR-031. This feature branch is stacked on PR179;
main and the public deployment have not changed. Natural-language/live-model and real
browser accessibility/deployed acceptance remain open.

Install `.[workflow]` or use the locked development environment with `uv run --extra workflow`.
Create a disposable local token file without printing its contents:

```sh
python3 -c 'from pathlib import Path; import secrets; p=Path("/tmp/pil-review-token"); p.touch(mode=0o600, exist_ok=False); p.write_text(secrets.token_urlsafe(48))'
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.review_web \
  --database /tmp/pil-review.sqlite --project atlas --token-file /tmp/pil-review-token --port 8001
```

Open `http://127.0.0.1:8001` on the server host. Enter the token through the password
control using your local secret-file viewer. The server has no external bind option;
localhost aliases, reverse proxy exposure and production deployment are unsupported.
The file must be owned, regular, private, non-symlink and contain 32..512 ASCII characters
without whitespace. Use a randomly generated capability. Never place it in a URL or CLI argument.
The page stores it only in memory and requires reauthentication after reload/lock.
Server-provided principal `local-demo`, tenant `synthetic-tenant`, site `lab` and the configured
project own every run. HTTP bodies cannot supply identity, scope, permissions or checkpoint IDs.

Authenticated GET routes: `/api/runs` (newest 50 owned records), `/api/run?run_id=...`,
`/api/events?run_id=...`, `/api/source?run_id=...&evidence_id=...`.
POST JSON routes: `/api/start` takes exactly `item,as_of`; `/api/recover` takes `run_id`;
`/api/review` takes `run_id,brief_id,digest,decision` (`approve` or `reject`).
All API calls require an Authorization bearer header, exact configured Host and any Origin
must match. No CORS, cookies, query tokens or client authority. JSON writes are capped at
8192 bytes; repeated JSON/query fields and unknown fields are rejected.

The page renders persisted canonical facts, scope/date, exact brief ID/version/digest and
snapshot/runtime versions. Missing quantities remain unresolved/not established. Source
lookup must belong to the persisted scoped brief and re-admits its original workbook or
metadata. Highlighting uses spreadsheet column coordinates. Source content is text, never HTML.
The timeline uses the application event allowlist and actual timestamps; it is a snapshot
feed and is separate from domain policy/evidence provenance and model streaming.

Approve saves one exact brief under the existing receipt/freshness/expiry policy; duplicate
approval acknowledges its existing result while rechecking current evidence. Reject saves
nothing. Approval cannot reconcile uncertainty or mutate sources. Recover reuses application
records and checkpoints after restart. Historical incompatible versions remain discoverable,
but resume/events/source access fail the immutable configuration check before checkpoint loading.
History is a bounded recovery aid, not a complete paginated run archive.

Errors: missing/wrong authentication 401; transport/scope denial 403; unknown run/evidence 404;
exact review/configuration/freshness conflict 409; malformed request or unavailable typed item
input 422; admitted source/checkpoint/storage failure 503. Public responses contain closed
codes/categories and safe messages, never raw errors, graph state, tokens or private prompts.
Status is a historical ledger read; an old status display does not authorize saving changed facts.

Suggested fixture walkthrough: Atlas GPU-A mismatch (8 required, 6 observed); GPU-C unresolved
requirement; GPU-D missing observation. Stop/restart the server while awaiting review, sign in,
select the owned run, recover and approve twice. Verify the same saved-result ID. These are
synthetic deterministic examples, not real-model quality or production procurement evidence.

## Actual installed browser evidence

The stacked [2026-10-04 acceptance slice](../project/browser-live-acceptance.md) adds real
headless Chromium keyboard/source/review/restart and representative narrow/wide checks.
Successful sign-in focuses the request field; a darker focus ring and wrapped review identifiers
correct observed browser defects. This supersedes the earlier absence of browser evidence for
these selected interactions, while deployment and comprehensive accessibility remain separate.

## Failure and asynchronous recovery continuation

The [bounded installed error-recovery slice](../project/browser-error-recovery.md), stacked on
#190, retains the selected exact brief after a failed replacement. New request inputs cannot
supply review authority. Page-owned safe errors exclude raw transport/response details. Lock
invalidates callbacks before follow-up requests; it does not cancel admitted server work.
An unknown save acknowledgment requires explicit owned recovery; repeated human review returns
the same durable result. No automatic retry is granted. Previous live acceptance has its original
application version; this changed page requires separate current-version live verification.
