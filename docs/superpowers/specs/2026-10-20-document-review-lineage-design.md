# Document-value review and correction lineage

Issue216; owner-authorized continuation of ADR038. Primary M2, parent41, part37/13.

The first review workflow is document_value, with an immutable task over one exact archived
snapshot/assertion. Proposed values keep that assertion's predicate, unit, source scope/version
and evidence. A domain-injected validator admits BOM Decimal quantities/prices, text SKU/description
or explicit null; unmapped fields and type changes are rejected. No unit/entity remapping.
Entity and operational workflows remain distinct unsupported variants.

ReviewProposal(scope, request_id, snapshot_id, previous SourceAssertion, proposed_value, reason,
proposer_id, workflow) is the immutable command. DocumentReviewTask(proposal, recorded_at) retains
the first server-owned aware timestamp, must follow original recording, and exposes a stable
scope/request-key task_id and SHA256 digest of its complete typed content. Reviewer identity is
from trusted RequestContext, never a proposal field. ReviewDecisionCommand(scope, request_id,
task_id, task_digest, outcome approve/reject, reviewer_id, reason) binds exact task content.
DocumentReviewDecision(command, recorded_at) has prospective effective_at=recorded_at. ReviewHistory
validates task binding/digest/time. Approval yields a distinct correction identity/value/evidence
and recomputation_required; downstream discovery is explicitly not_evaluated. No source fact is
rewritten and no canonical/governing value is selected, including across contradictory approved tasks.

Both creation and decision require REVIEW plus READ_EVIDENCE and matching RequestContext tenant/project/site; reads
require READ_EVIDENCE. Exact StateScope/version always scopes persistence. Operational contexts
without REVIEW cannot propose/decide. Separate trusted local CLI composes these permissions from
PIL_DOCUMENT_REVIEWER_ID and exact scope; no actor/permissions/time arguments or JSON overrides.
This local shell boundary is not production authentication or a new operational-agent tool.

DocumentReviewJournal: propose(proposal, recorded_at)->task; decide(command,recorded_at)->decision;
get(scope,task_id,as_of=None)->ReviewHistory; history(scope,as_of=None)->tuple[ReviewHistory,...].
Exact command retry preserves the first stored timestamp, despite a later clock value. Reusing
request identity for changed content conflicts. A task has one terminal decision; concurrent
identical decisions converge and opposed/new decisions conflict. A decision cannot precede its
task. As-of is aware and inclusive: a task before creation is not-found; a later decision is absent
from the earlier view (pending), never an applied correction. History orders by recorded_at/task_id,
not source precedence. Null remains unresolved and distinct from numeric zero.

Postgres owns additive version1 pil_document_review_meta/tasks/decisions tables, payload hashes,
foreign membership links to archive schema1, transaction locking and append-only SQL guards.
Explicit init requires initialized archive1; it never changes prior archive schema or records.
No implicit init/migration. New writes are atomic, retained reads revalidate typed graph, hashes,
keys, exact original assertion membership and decision binding. The existing registered graph codec
is reused with explicit new records/enums at bootstrap. Database-owner coordinated tampering is
outside this bounded integrity promise. Connection strings/raw errors never leave the adapter.

Public interfaces.document_review: init; propose --scope scope.json --input proposal.json;
decide --scope scope.json --input decision.json; show --scope ... --task-id ... [--as-of ...];
history --scope ... [--as-of ...]. Proposal JSON has exactly request_id,snapshot_id,assertion_id,
workflow,proposed_value,reason. Decision JSON has exactly request_id,task_id,task_digest,outcome,reason.
Typed value JSON is {type:decimal,value:string}, {type:str,value:string}, or {type:null,value:null}.
Output includes previous/proposed typed values, original evidence, principals, timestamps, exact
binding digest, decision and optional accepted correction. Unknown IDs/scope, malformed/unsupported
input, altered digest, terminal conflict, corruption and DB failure return typed errors/exit2;
no partial-success stdout. init is trusted local administration and needs only DSN.

Acceptance: RED/GREEN intrinsic boundary tests, real isolated Postgres concurrency/retry/conflict/
rollback/corruption/source-membership/SQL-guard contracts, real subprocess restart/as-of/denial,
clean installed wheel both default and storage paths, full make check +coverage ratchet, existing30
challenge/mutations, independent exact-head source/receipt review, revision-bound semantic JSON.
No shipped defect or model swap. Broader13/37/41 remain open for other workflows, downstream traversal/
controlled recomputation, source-governing policy integration and production qualification.
