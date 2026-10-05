# ADR-031: Authenticated local browser review transport

Status: accepted for the bounded fixture demo branch. Primary #74; part of #67/#68.
Builds on ADR-019, ADR-028, ADR-029 and ADR-030.

Expose the existing fixture workflow through a separate loopback HTTP composition root.
The operator supplies a private regular token file and one admitted project. A bearer
capability authenticates a fixed synthetic human reviewer; the server owns identity,
scope and permissions. The page keeps the token in memory only and clears the input.
It does not store it in URLs, cookies, local storage, logs, audit events or checkpoints.
Restarting the page requires authentication again. This is a local development capability,
not production identity, delegation or public hosting; bind only IPv4 loopback.

Require the exact server Host, reject foreign Origin/Sec-Fetch-Site, require JSON for
writes and a bounded body. Authorization headers cannot be supplied by cross-site HTML
forms; no CORS opt-in is provided. All responses are non-cacheable and the page uses a
self-only content policy. Production transport security/authentication remains open.

Owned run discovery queries the application ledger before decoding and returns at most
50 records in stable newest creation order. Historical versions remain discoverable;
resume still checks the immutable application configuration before checkpoint loading.
Only application event DTOs reach the timeline. It is a snapshot feed, not framework
streaming. Source drill-down requires membership in the exact scoped persisted brief.
Review carries displayed brief ID/digest; receipts and saved-result authority remain in
the application ledger, including expiry, freshness and replay checks.

Costs: another local transport and bounded recent history; no multi-user identity,
public exposure, live inference, hard cancellation or complete streaming contract.
