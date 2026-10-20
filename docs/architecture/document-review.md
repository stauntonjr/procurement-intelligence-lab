# Durable document-value review

Issue #216 (M2, parent #41, part of #37/#13) follows the [assertion archive](assertion-archive.md).
ADR-039 and the [written contract](../superpowers/specs/2026-10-20-document-review-lineage-design.md)
define this first workflow. The old demo/brief approvals and governing-claim policy are unchanged.

One task retains an exact archived assertion, original evidence and typed previous value, a proposed
value with unchanged predicate/unit/scope, rationale, proposer and server recording time. A human
approve/reject decision binds the complete typed task SHA256 digest and records reviewer, rationale
and prospective effective time. Exact request retries return the first recorded task/decision;
changing a reused command or making a second terminal decision fails. Separate contradictory
approved tasks remain retained; history never selects the latest one as governing truth.

An accepted correction is a separate record linked to the original assertion, task and decision.
It does not rewrite source assertions, normalize a new value, update entity identity or select a
governing requirement. Its output says `recomputation_required: true`, `downstream_status:
not_evaluated`, and `governing_state_updated: false`. Downstream traversal/invalidation/recomputation
and integration with authority policies remain subsequent #35/#37/#41/#46 work. Null stays explicit
unknown, distinct from numeric zero. Entity, operational and unmapped-field reviews fail explicitly.

Use the same private `PIL_ASSERTION_ARCHIVE_DSN` and an initialized archive schema1. The separate
human shell boundary also requires `PIL_DOCUMENT_REVIEWER_ID`. Neither identity, permissions nor
recording timestamps can be supplied by request JSON. This trusted local configuration is not
production authentication; no operational-agent tool receives review capability. Application APIs
require REVIEW plus READ_EVIDENCE and matching RequestContext scope before proposing/deciding;
reads require READ_EVIDENCE and exact scope/version.

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.document_review init
uv run --extra storage python -m procurement_intelligence_lab.interfaces.document_review \
  propose --scope scope.json --input proposal.json
```

`proposal.json` has exactly these fields; obtain both IDs from a real archived result:

```json
{
  "request_id": "review-C2-v1",
  "snapshot_id": "<archived snapshot_id>",
  "assertion_id": "<assertion_id for the target source field>",
  "workflow": "document_value",
  "proposed_value": {"type": "decimal", "value": "8.00"},
  "reason": "Human interpretation after checking the captured source cell"
}
```

Values are exact finite decimal strings for quantities/prices, nonblank strings for SKU/description,
or `{ "type": "null", "value": null }`. Booleans, JSON floating-point numeric proposals, unit changes,
unknown fields, duplicate keys and client authority/time overrides are rejected.

Read `task_id` and `digest` from the task output. `decision.json` has exactly `request_id`, `task_id`,
`task_digest`, `outcome` (`approve` or `reject`) and `reason`. Then use:

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.document_review \
  decide --scope scope.json --input decision.json
uv run --extra storage python -m procurement_intelligence_lab.interfaces.document_review \
  show --scope scope.json --task-id TASK_ID
uv run --extra storage python -m procurement_intelligence_lab.interfaces.document_review \
  history --scope scope.json --as-of 2026-10-20T12:00:00+00:00
```

As-of timestamps are aware/fixed-offset and inclusive. Before task creation, show is not-found;
a later approval is absent from an earlier pending view. As-of does not select source authority.
Explicit init adds review schema1 tables with immutable guards and foreign keys to archive membership;
it leaves existing archive schema1 and bytes intact. Other operations never initialize or migrate.
Driver/connection details stay private. Typed review failures use input contract/not-found, policy
conflict, infrastructure integrity/unavailable codes; the CLI returns exit2, sanitized stderr JSON,
no partial-success stdout. Existing scope/archive failure codes also remain valid.

Real Postgres contracts cover rollback, concurrent identical/opposed commands, corruption and
source membership. Actual CLI and clean-wheel storage probes check restart, exact digest rejection,
prospective history and original-source preservation after source deletion. Storage qualification
requires the dedicated test DSN; skipped storage checks are not durability evidence. Broader
#13/#37/#41 remain open, with no UI, automatic recomputation, production service or deployment claim.
