# Completed planned-prefix archive design

Status: proposed for maintainer review; not an accepted policy or implementation plan.
Decision [#228](https://github.com/stauntonjr/procurement-intelligence-lab/issues/228), proposed
[ADR-044](../../adr/044-atomic-planned-prefix-archive.md), primary M2, parent #37,
Part of #13/#35/#36/#12/#75. Baseline main `8e72f8730730c93bdfbd56c646f67ca65a6bec83`.

## Intent and current evidence

The owner resumed foundational architecture after demo cycles and instructed continued work.
The proposed next slice connects real package execution to durable evidence before expanding
stage coverage. Success means a fresh process can recover the exact admitted plan, actual
five-stage result, twelve dispositions and original source bytes after the source disappears.
This proposal assumes completed-result durability is the next priority; no wider-stage policy
or implementation authorization is inferred from the instruction to proceed.

PR #227 / ADR-043 supplies actual synchronous INGEST-through-ASSERT execution. ADR-038 / #213
supplies atomic source snapshots and content through AssertionArchive. The current
ArchivedDocumentStages calls the legacy pipeline; it is not a sink for planned execution.
PlannedBomExecutionService retains no durable receipt. DocumentSnapshot contains no physical
plan, resolved-reference digest set or twelve-entry execution receipt. PhysicalPlan contains
canonical_json bytes, which the current allowlisted SemanticCodec cannot serialize.

Same-baseline advisory [39691201487](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/39691201487)
succeeded using one bounded Gemini request. Its next-stage recommendations remain advisory.
Direct Project review confirmed #14/#36 remain broader unscheduled work and #37 is in progress;
the deterministic audit had no missing configured fields, labels, milestones or views.
Reviewed governing Issues: #12/#13/#14/#20/#21/#32/#33/#35/#36/#37/#41/#75/#213/#225/#226;
ADRs 001/017/022/037/038/039/040/041/042/043 retain their existing authority boundaries.

## Options and recommendation

1. **Archive completed planned prefixes.** Reuse source materialization and add a typed,
   atomically committed execution binding. This closes the current provenance gap with no
   new entity algorithm or authority policy. Recommended.
2. **Adopt RESOLVE next.** Adds a sixth actual stage but needs candidate catalog, scoring,
   abstention/review and benchmark decisions under #14. The existing prefix remains ephemeral.
3. **General job/attempt processing.** Addresses #36 more broadly but introduces admission,
   scheduling, retry and lifecycle policy beyond retaining an already completed computation.

## Authoritative contract

Inputs are one intrinsically valid PrefixExecutionReceipt with its complete typed output chain,
the exact captured bytes, and explicit normalization-policy parameters. They must come from
the actual admitted runner, not a fixture plan, serialized success flag or second legacy run.
The application derives the existing DocumentSnapshot from retained outputs only.

Output is an immutable archive acknowledgement binding scope, execution_digest, the first
retained receipt_digest, the exact source snapshot and its existing ArchiveReceipt, plus a
monotonic binding sequence. Sequence gaps are valid; sequence order is not governing effectivity.
No additional timestamp pretends to be a database commit time. The retained execution receipt
keeps its actual server completed_at; the existing source receipt retains its current time rules.

The new frozen core record must intrinsically validate exact encoded equality between every
snapshot field and the receipt output: source, artifact, structure, mapping, observations,
assertions, auxiliary mention claims, origin, all five events and normalization policy. Require
the existing canonical parameter representation and verify its parameter-instance reference and
content digest at explicit domain composition. Reuse strict output/receipt constructors; do not
weaken their timestamp, immutable-container, retained-plan or lineage guards for persistence.

Scope is the complete tenant/project/site/version. Observed, captured, assertion-recording and
execution-completed times remain distinct and offset-preserving. No as-of winner, latest source,
freshness, correction selection or canonical entity is inferred. All twelve declarations remain
bound; seven later entries are NOT_EXECUTED, including unvisited EMPTY declarations.

## Identity and first-retention policy

Use `(scope, execution_digest)` as the durable computation key. The digest already binds exact
plan bytes/config hash, execution context/code, source, resolved declarations/instances/content,
typed output and twelve entries; it excludes only server completed_at.

- First append stores the complete actual receipt and exact source evidence in one transaction.
- Same computation and bytes return the first retained binding/receipt without new source,
  claim-membership or execution-binding rows. A later completed_at alone is allowed to converge.
- Compare complete canonical computation payload and source bytes, never merely matching IDs,
  Python datetime/dataclass equality or a caller-supplied digest. Any other difference under
  the same key is a typed conflict; persisted corruption is a typed integrity failure.
- A changed source URI/version/content, scope, run/context/code, plan, selected implementation,
  outside-prefix metadata or policy material changes computation identity and can form a new
  independently retained result. A reused URI/run label is not request idempotency.
- Concurrent identical candidates converge on the same first acknowledgement. No update/delete
  API, last-writer overwrite or hidden preference among conflicting claims is introduced.

Every execute invocation still performs the five real stages. Archival does not authorize a
lookup to skip processing. A source-less recovery uses the explicit archive reader. Failure
after a possibly committed transaction never establishes that nothing was written; an operator
can inspect scoped history and retry equivalent retention. Automatic job recovery is outside scope.

## Ownership and transaction boundary

Add neutral frozen completed-execution records and a separate PlannedExecutionArchive Protocol.
Its responsibilities are readiness, atomic append, exact scoped load, bounded history and source
content. It may reuse shared archive contracts but does not expose a connection or driver type.
Core does not import PostgreSQL, a domain, interface parsing or an external framework.

An application coordinator performs existing full runtime admission, archive readiness, the
actual runner, snapshot projection and retention. Bootstrap injects actual executors, one shared
staging content store, policy validators, clock and the port. Do not invoke legacy `.run()` to
rebuild a result already produced by the runner; do not put persistence callbacks in DomainPackage.
The existing default application and ephemeral service retain their behavior.

The Postgres adapter uses one transaction for source content/snapshot/claims/membership and the
completed-execution binding. A shared transaction helper may preserve the old append mechanics;
two independently committed public append calls do not satisfy this design. Validate/reuse an
existing source snapshot exactly, maintain consistent lock ordering, and roll back every new row
on a mid-write failure. Database-owned sequence gaps do not indicate partial evidence.

Add explicit `planned_prefix_archive/v1` metadata and immutable binding storage. Existing
archive1/review1/dependency1/approved-correction capabilities and existing tables/rows/IDs remain
unchanged. Explicit new-capability init requires a supported initialized source archive; it is
idempotent only for the exact supported capability and never silently migrates an unknown version.
Reads/appends must not initialize it. Missing capability fails before source access; incompatible
persisted metadata fails closed. Existing SQL immutability protections apply to new records.
Database owners can bypass guards; checksums are not an adversarial tamper-proofing guarantee.

## Portable representation

Use the existing bounded content-addressed typed graph with an explicit bytes scalar encoded as
`["bytes-hex", "lowercase even-length hex"]`, including the empty-bytes case. Bound the full wire
before decoding and reject malformed, uppercase/noncanonical, odd-length or unsupported values.
Keep the existing 16 MiB wire, 50,000-node and depth64 limits. Source bytes remain separately
content-addressed; the graph contains the canonical plan bytes, not a second source blob.

Bootstrap explicitly registers the new records, PhysicalPlan, the five stage outputs, execution
entry/reference/receipt types and their concrete enums. Decoding cannot import a class named by
data, execute callbacks or use pickle. Constructor and canonical-plan validation run on load;
matching hashes are insufficient. Reject unknown roots/types/fields/tags, duplicate keys, orphan
nodes, invalid memberships, inconsistent digests and unsupported capability versions.

Existing DocumentSnapshot wire bytes/node hashes must remain unchanged for identical values.
New execution roots live only in new capability storage; old source rows must not acquire new
wrapper types. Old source/archive/review/replay callers must read newly archived source snapshots
and continue to operate on their original values. This is additive capability evolution, not a
rewrite of the original archive schema or a new general serialization framework.

## Public caller and failure behavior

Keep `interfaces.execute_package` unchanged when `--archive` is absent. With the explicit flag,
use the existing environment-only `PIL_ASSERTION_ARCHIVE_DSN` and optional storage extra. Parse
and admit all runtime metadata, then check storage readiness before reading source content.
Execute five stages once; retain atomically; print one success JSON document only after commit
acknowledgement. Do not print a successful prefix before a failed archive operation.

Opt-in success adds `archive_receipt` and `retained_execution_receipt`. The existing
`execution_receipt` describes the current actual invocation. On retry, its completion/digest can
differ from the first retained receipt; both must have the same computation digest. Do not label
the retained result as a new computation or claim a durable attempt journal/result cache update.

New `interfaces.planned_execution_archive` commands:

- `init`: explicitly add the capability after supported source archive initialization.
- `show --scope FILE --execution-digest ID`: reconstruct the first retained result/receipt.
- `history --scope FILE --limit N --after-sequence N`: list only execution bindings, in sequence
  order; default100, maximum200, positive limit and nonnegative cursor. No latest-winner meaning.
- `content --scope FILE --execution-digest ID --output PATH`: verify and export original bytes
  atomically to a new path, preserving the existing no-overwrite guarantee.

Readers never access the original source URI, current planner/config files or executors. Validate
retained policy and semantic evidence through injected validators. Missing/foreign scope is
not-found; empty scoped history is valid, while absent/corrupt content is not an empty success.
The history cursor is exclusive, with0 meaning the initial page. Return `has_more` based on an
actual additional matching row and `next_after_sequence` equal to the last returned sequence
only when more rows exist. An empty page has no next cursor. Do not infer a total count or
complete history from reaching a page limit.

Reuse applicable ArchiveContract/Conflict/Integrity/NotFound/Unavailable and package-execution
failure categories. Input mistakes and unavailable driver/capability/backend fail typed; corrupt
stored output fails integrity rather than being returned. Preserve sanitized JSON stderr, exit2,
empty success stdout on failure, strict bounds/Unicode parsing and no DSN/driver/secret exposure.
This is a trusted local developer interface, not multiuser authentication or agent authority.

## Required acceptance evidence

| Family | Required counterexample and positive proof |
|---|---|
| Empty/missing/unknown | Real empty batch retains five events/twelve entries; absent capability/content is typed; unresolved fields stay unknown, never zero |
| Multiplicity/conflict | Duplicate/conflicting rows remain separate; exact and concurrent retries preserve first binding; different same-key canonical content conflicts |
| Scope/time | Cross-scope reads are not-found; offset substitutions fail exact validation; distinct completion alone converges while original completion remains retrievable |
| Numeric/bounds | Quantity0/negative/fractional and explicit unit/currency policy remain unchanged; graph/input/history bounds reject rather than truncate |
| Malformed/unsupported | Missing driver/capability and incompatible runtime fail before source I/O; invalid bytes tag, plan shape, graph, metadata and membership fail typed |
| Public/artifact | Actual compiled-plan CLI -> Postgres commit -> source deletion -> fresh-process show/export; clean base/optional wheels and legacy source archive reader |
| Safe counterexample | Forbid every executor/source read during recovery; injected mid-transaction failure leaves no partial new evidence; ambiguous acknowledgement never claims rollback |

Also verify immutable SQL guards, changed policy/plan/context identities, exact hashes and source
export, base-wheel unavailable-storage behavior, no repeated legacy pipeline, existing archived
review/replay paths and no new schema/driver default. Require full make check/coverage ratchet,
clean package smoke against a task-owned disposable Postgres, all existing public/known-bad
challenges, latest-revision semantic JSON and independent semantic/architecture review. A shipped
semantic defect, if discovered, needs its own regression oracle and challenge manifest.

## Delivery boundary and review gate

No later-stage execution, neutral semantics, jobs/attempt states, queue/listener, automatic retry,
governing state, correction-triggered work, new model/algorithm, production auth/deployment,
backup/HA or full milestone acceptance. Original claims and old callers remain authoritative.

This is the concrete proposed design for owner review. After ratification, create a separately
scoped implementation Issue and written plan; review that plan before product changes. Decision
#228 remains open until approved decision artifacts merge. Do not mark any runtime, storage,
public-caller or artifact acceptance complete based on this documentation proposal.
