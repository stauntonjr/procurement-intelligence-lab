# Exact brief review/save v1

Primary #67; part of #68/#53/#72. Extends ADR-028 under the approved G2 plan.
This slice implements application-owned review persistence before optional graph integration.

Authoritative inputs: owned immutable run/configuration, exact item and aware as-of request,
freshly admitted core investigation, server RequestContext and clock, configured approval TTL.
Output: immutable deterministic brief, exact approval/rejection receipt and one durable saved
result. Scope is run owner plus tenant/project/site. The brief binds run/query/attempt, versions,
request, snapshot and canonical core facts/source references. No model arithmetic or narrative
is introduced in this slice. A newly drafted version becomes active and invalidates old approval.

Review requires READ_STATE, READ_EVIDENCE and REVIEW, save additionally ACT; read/draft requires READ_STATE
and READ_EVIDENCE. In this bounded demo the initiating human is the required reviewer. Runtime
agent composition never receives REVIEW/ACT. Local CLI uses a separately documented fixed human
identity; it demonstrates policy/restart mechanics, not production authentication.

Receipts bind brief ID/digest, run, reviewer, decision and aware expiry. Repeated identical review
returns the original receipt without renewing expiry. Rejection is terminal for that version.
Save requires the exact active approved brief/digest and application-issued idempotency key;
rechecks current core snapshot and canonical facts, permissions, configuration and expiry. A
transaction atomically checks active version/receipt and inserts one saved result. The trusted
clock is evaluated after acquiring write serialization, so waiting cannot extend approval.
Reads compare the complete embedded run against the authoritative run ledger. Relational IDs/keys
and receipt chronology are validated before replay; existing briefs with missing active state fail. Exact save
replay returns the same result even after expiry, because it acknowledges a previously completed
write; it still rechecks current scope, digest/key and evidence. Changed content/evidence or
cross-run receipts fail closed. Approval does not change procurement state or resolve conflicts.

Stored briefs, receipts and saved results are the durable audit; checkpoint state grants no
permission. A process crash after save can replay to the same result. Missing or corrupt state is
never an empty success. Store failures are infrastructure; unknown IDs input; stale/altered,
rejected, expired or non-approved requests policy failures. Original document instructions are
retained only as untrusted evidence and cannot supply a receipt or policy.

Scenario families: empty/missing unknown IDs; repeated/concurrent review/save and altered replay;
owner/project/as-of/expiry boundaries; negative/zero TTL rejected (no quantity policy changes);
malformed/corrupt records; real CLI processes and clean wheels; source changes and non-reviewer
permissions block save. Graph interrupts, model draft validation, browser review controls and
live inference remain separate acceptance gates.

## Supersession and stale-item correction

An intact owned active pointer remains required for completed-save acknowledgment. It may name
a newer brief: supersession prevents a new write from old approval, while replay of an already
completed write returns its same saved result after the unchanged current-evidence/authority
checks. Missing, dangling or foreign active pointers fail as stored-state corruption. A previously
reviewed item absent from newly admitted sources yields typed brief conflict and no save.
