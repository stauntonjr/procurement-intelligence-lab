# Required-quantity RECONCILE from retained RESOLVE producers

Status: **owner-approved design at `2c1b759768cfd577c3d9e4a589b655d390b46c9f` on 2026-10-24; implementation plan awaiting review**.
Decision intake: [#238](https://github.com/stauntonjr/procurement-intelligence-lab/issues/238), M4, native parent #20.
Baseline: main a8de65db7ae6b6192a937ae930859d1b205be5aa / PR237.
The owner approved this exact written design at `2c1b759` and instructed proceed. This selects
the retained-producer approach and the first-profile restrictions below. No product code or
implementation acceptance is supplied here. Preserve Native/inline implementation and one
independent final review; do not ask for a new execution method. The [executable plan](../plans/2026-10-24-retained-resolve-reconciliation.md)
and implementation [#239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239) record the next work; plan review is pending.

## Intent and governing work

Turn actual, retained canonicalized source claims into a reproducible required-quantity governing
decision and optional expected-state projection. The same scoped evidence must explain why an
approved revision governs, why equal competing revisions jointly govern, or why conflict abstains.

Existing ratified semantics are ADR020/023/024, policy
[procurement-governing-claims/v1](../../product/governing-claim-policy-v1.md), and closed
Issues15/46/47. Open #118 constrains state construction. #20/#12 cover package/runtime adoption;
#14/#42/#39/#43/#45 remain wider identity work. #36 covers separate ingestion/job work.
[Post-merge orientation](../../project/audits/2026-10-24-post-resolve.md) records the new audit.

## Approaches and recommendation

1. **Recommended: a recorded-producer RECONCILE operation.** Consume explicitly selected,
   independently validated six-stage archived producers. Invoke one actual seventh-stage strategy;
   retain its governing decisions and expected state. This isolates the missing authority/evidence
   bridge and exercises multi-revision conflict without inventing batch capture/orchestration.
2. **Fresh multi-document seven-stage execution.** Run the first six stages for each supplied
   source, join those outputs, then reconcile. This gives a single fresh command but requires a
   new batch-execution/receipt contract and broader source/capture failure rules. Defer until the
   governing bridge is qualified; do not fake a single linear prefix from several invocations.
3. **Alternative direction: durable RESOLVE local jobs.** Adapt the six-stage profile into a new
   explicit job contract. This strengthens durability but leaves the governing-state gap open.

Owner approval selects approach1 and the bounds below. The deferred alternatives are not selected.

## Exact delivery boundary

The new profile is **retained-resolution-reconciliation/v1**, an explicit synchronous operation
with historical producers. It is not a seven-stage fresh-prefix receipt, a general resume/cache
engine, or a seventh-stage durable job. The original five/six-stage types, manifests, public
commands, archived wire formats, digests and jobs remain unchanged.

The current operation invokes RECONCILE exactly once. Its receipt retains all twelve standardized
stage dispositions: RECONCILE SUCCEEDED and the other eleven NOT_EXECUTED for this invocation.
Each historical producer retains its own six actual successes, events and complete receipt.
Separate `recorded_producers` and `current_operation` projections prevent confusing historical
success with new execution. Requested-operation completion is true only after validated output;
package execution completion is always false. DERIVE through ACT are not invoked.

A dedicated, explicitly versioned procurement source/operation profile binds RECONCILE to
`procurement.reconcile/governed-required-quantity@1` and exact policy-v1 content. Do not change the
old bom-table binding or silently replace explicit-source-precedence behavior. Compilation and
runtime admission still inspect a complete fixed-topology manifest and explicit registry/config;
only the chosen RECONCILE executor is constructed for this operation. Producer validation needs
no current upstream executor. No new stage, logical mode or arbitrary DAG is introduced.

## Authoritative inputs, scope and time

A trusted local caller supplies:

- one to eight exact scoped six-stage execution digests already retained in the selected archive;
- an exact StateScope (tenant/project/site/version), aware query as-of and fresh operation context;
- bounded explicit source-authority metadata, the supported governing-policy reference, compiled
  operation manifest and deployment registry/config.

Archive reads are explicit. The CLI requires the existing optional storage capability to load
producers even when result append is not requested. Base installation stays dependency-free and
reports typed unavailable-storage failures; there is no ambient catalog or hidden file import.
A future portable export-input mode is separate. Reusing old archived results is never described
as a newly executed prefix.

Every input digest must exist in exact supplied scope. Load and independently validate the full
recorded six-stage graph, recorded policy/catalog bytes, retained first-five binding and original
source bytes with the existing source-free reader. Use recorded policy content, not a newly
constructed upstream runtime. Reject duplicate execution digests, repeated source artifacts and repeated source content hashes
within the selected set. This includes identical bytes with different declared revision IDs or
approval records: this first profile does not treat relabeling/copying identical bytes as independent
authority. Distinct-content revisions may still assert equal quantities and jointly govern.
All producers must use the same exact candidate semantic snapshot and supported internal-SKU
namespace/policy, so a local key from unrelated catalog identities cannot be joined silently.
Every producer is bounded by existing codec limits; reject an oversized aggregate before invoke.
The implementation plan must pin an aggregate decoded-byte/node budget no larger than the sum
of the existing eight individual bounds and test it through the real caller.

Input scope.version identifies this supplied source-analysis scope; document revision IDs are
separate metadata. All source scopes must match exactly. Governed output scope.version is the
ADR024 policy-decision identity, not an arbitrarily selected source revision. Preserve original
source version/scope on every evidence path.

Query as-of cannot be after operation started_at. Producers must already exist and their capture
cannot be after operation started_at. Query as-of may precede a producer's ingestion: policy v1
uses approval/effective intervals for historical authority, not ingestion order. Document and
capture/ingestion times remain visible and do not win authority. Preserve fixed timezone offsets
in identity/audit encoding; compare aware instants for temporal eligibility.

## Explicit authority metadata and supported row shape

The metadata file is at most64KiB UTF-8 JSON with strict unique/exact fields, no nonfinite values
or lone surrogates. It contains one record per selected producer and no extras. Each record pins
the exact producer execution digest, source artifact/content identity, revision_id, superseded
revision IDs, source role, approval record reference/approved_at, effective_from/effective_until
and declared document time. Scope and ingestion time come from the validated producer rather than
caller overrides. Raw metadata bytes/checksum and canonical semantic identity remain distinct.
The implementation plan pins exact schema/version/field/nullability/bounds before coding.

These are trusted local **synthetic caller attestations**, not verified enterprise approvals,
signatures, external review authorization, or authority granted by a model. Null approval is
unapproved. A source role named approved_bom_revision alone grants no approval. A nonnull approval
requires its nonblank record reference and aware approval time. Missing mandatory JSON fields
reject admission; valid explicit absence of approval yields the existing policy's ineligibility.
No approval, effective time, supersession or revision relation is inferred from filenames, larger
revision labels, source order, document time or ingestion time. Do not mint human-confirmed state
or accept human reconciliation selections in this slice (ADR034 remains separate).

First-profile row restriction: at most one actual quantity assertion per resolved canonical item
in each selected BOM revision. More than one row for that item/revision, duplicate revision/source
membership, unknown/missing quantity, negative quantity, or unsupported normalized quantity unit
is a typed **unsupported reconciliation input**, before executor invocation. Preserve and return
producer recovery IDs; the six-stage source remains valid and queryable. This profile does not
invent aggregation or deduplicate equal rows. All source assertions and resolution decisions stay
unchanged. A later row-aggregation contract requires explicit semantics and its own evidence.

Non-quantity claims are retained and classified as outside this predicate. Unresolved/blank-SKU
rows retain their original unlinked claims. If a source contains unresolved item identity, it
cannot assert a complete item-level requirement in this first profile: reject it explicitly,
rather than silently computing a partial required quantity. A truly empty, validated producer
is valid: one real RECONCILE event, no candidates, decisions or state; never fabricated zeros.
For any supersession edge between two selected revisions, their resolved item-key sets must be
identical. A selected successor that omits a predecessor item (including an empty successor after
a nonempty predecessor) is unsupported and rejects admission before invoke. Existing policy v1 is
item-candidate-local; do not preserve the old value by accidentally hiding a document-level edge,
invent a zero, or infer deletion. Supersession references outside the selected input universe stay
recorded and have no unselected candidates to suppress; no global completeness claim follows.

## Domain policy and neutral stage contract

Implement the existing framework-independent ReconcileStrategy protocol in procurement. Its
input is the exact admitted canonicalized quantity claims plus explicit operation-owned authority
context supplied through composition. Do not manufacture canonicalized assertions from unresolved
mentions. The strategy calls the existing required-quantity governing policy; it does not call
legacy reconcile_lines or choose an eligible source by order.

For each canonical item, create a policy candidate bound one-to-one to its supported source
quantity assertion, authority metadata and exact EvidenceRef. Policy v1 governs approval at or
before as-of, start-inclusive/end-exclusive effective intervals and explicit supersession:

- no eligible active candidate: unresolved, no state;
- one eligible value: governed with that candidate and losing evidence retained;
- multiple eligible exact-equal value/unit candidates: governed_shared_value with all evidence;
- differing eligible values/units: unresolved, no quantity/state;
- no implicit unit conversion, tolerance, revision precedence or summation across revisions.

Retain policy-level decisions including every governing/losing candidate and disposition. Neutral
ReconciliationDecision records contain exactly the corresponding canonicalized quantity claims,
status, policy ID, rationale and current deterministic provenance. Preserve the domain's shared-
value distinction in a domain audit record; do not change the old neutral status enum to encode
procurement-specific outcomes. Add explicit audit reasons for future approval/ineligibility;
do not mislabel an excluded candidate as eligible or silently alter the existing legacy caller.

Project only governed values to OperationalState with a required_quantity StateAttribute,
EpistemicStatus.OBSERVED (the selected numeric value is directly source-observed), unit each,
complete unique governing source evidence and exact as-of. A separate procurement audit records
ProcurementStateBasis.RECONCILED; do not add a procurement policy state to the shared epistemic enum. Scope
version follows ADR024 using policy ID, item, exact aware as-of and ordered governing claim IDs.
The neutral reconciliation_id points to the exact neutral decision; retain the domain governing
ID separately. First-profile freshness is UNKNOWN: being policy-governed does not prove current
source coverage. Do not create ObservedProcurement, outstanding quantity, price, delivery state,
DerivedFact or human-confirmed authority. Zero is a valid governed quantity; unresolved is no state.

Independent domain postconditions validate each candidate's source membership/value/unit/scope,
policy and metadata binding, exhaustive governing/losing classification, all dispositions, exact
projection/evidence, and complete unconsumed claim IDs. Neutral runtime guards validate immutable
links/provenance/registered metadata without importing procurement. Failure after invoke is a
contract failure, not an invented successful empty result.

## Retention, recovery and identity

Composition stays in bootstrap; core owns policy and semantic guards, adapters own DB/CLI mechanics.
Introduce distinct immutable request/invocation/output/operation receipt/archive records, a neutral
archive port, and finite codec registrations. Never widen old request/receipt/job constructors.

Every computation identity binds the explicit complete plan, context, exact producer computation
identities and full admitted content, canonical authority metadata, policy and actual seventh
output. Exclude current completion time and metadata raw-format differences from computation;
retain both in receipt identity. Preserve producer audit receipts separately. Same-digest checks
must compare full admitted content, not digest alone. Source/metadata ordering is canonical and
reordering cannot choose a governing source.

Opt-in append uses a new explicitly initialized `retained_resolution_reconciliation/v1` capability
beside existing archive tables. It requires prior resolved capability readiness. Selected producers
must already exist and be verified; no implicit import/capture/recompute. One transaction retains
current result, exact producer archive-receipt links, policy/authority evidence and output. Exact
same-computation retry retains first result while a new call still invokes RECONCILE once. Show
current and first-retained receipts separately. Lost acknowledgement never implies rollback.

The reader loads all linked retained producer evidence and revalidates recorded domain policy,
metadata and decision/projection without original metadata/config/source files, current executors,
file paths or model/network access beyond the chosen DB. Present-row broken joins, unsupported
recorded policy, resealed swapped rows/metadata or inconsistent producer receipts fail integrity.
Exports contain the complete bounded result/authority/producer-reference graph; original source
bytes and complete producer exports remain available through existing six-stage readers. Do not
advertise the new export alone as self-contained source evidence. SQL ordinary-write immutability
is required; arbitrary coherent rewriting by a DB owner is outside the authenticity boundary.

## Real caller and failures

New explicit `reconcile_resolved_package` CLI takes scope/context/as-of, repeated producer digest,
manifest/registry/config, policy/authority input and optional --archive. DSN stays in
PIL_ASSERTION_ARCHIVE_DSN. A separate reconciliation-archive CLI supports explicit init,
show/history/content-manifest/export with bounded cursor and atomic no-overwrite exports. An
export manifest maps producer digests to existing source/graph recovery commands; there is no
fabricated single combined XLSX. Exact command/schema names are frozen in the approved plan.

Validate bounded argument/JSON/namespace/runtime metadata before opening storage; then check
capability and validate all selected producers before invoke or append. Distinguish admission,
unsupported input, invoked-output contract, archive unavailable, scoped not-found, immutable
conflict and corrupt retained evidence. Errors are sanitized JSON/exit2 with known scope/producer
recovery IDs, no DSN/settings/traceback. Missing/foreign scope cannot fall back to another record.
No current source read, executor invocation or write is allowed on a failed admission.

## Acceptance and scenario families

| Family | Required evidence |
|---|---|
| Empty/missing/unknown | Actual empty producer -> real empty seventh event; no producers invalid; missing metadata fields reject; null approval ineligible; unresolved identity/missing quantity unsupported and source retained; no synthetic zero state. |
| One/many/duplicate/conflict | Unique governed, equal jointly governed, conflicting revisions abstain; order permutation invariant; duplicate producer/source/content/revision and repeated item rows reject; selected supersession item-set mismatch rejects; all losing/evidence retained. |
| Scope/time | Exact input scope/catalog; wrong version/namespace rejects; approval/effect start/end/equal instants/offsets; expired and future metadata dispositions; ingestion order never wins; derived output scope identity. |
| Numeric | Valid zero/fractional values; negative/unknown/multiple rows fail supported-profile admission; exact equality and differing units; no sum across revisions or implicit conversion. |
| Unsupported/malformed | Missing driver/capability; strict JSON and all bounds; settings/descriptor/version/code pins; unsupported policies/predicates; malformed or resealed producer graphs fail before invoke. |
| Public/artifact | Real subprocess init/load/run/archive/restart/delete metadata/show/history/export; clean base wheel typed-unavailable and clean storage wheel success; no helper-only acceptance or skipped storage qualification. |
| Safe counterexample | Source-precedence and five/six-stage public/digest/codec/job paths unchanged; unknown observations remain unknown; no historical invocation claim, cache, authority widening, DERIVE/ACT or seven-stage job support. |

Use disposable Postgres for transaction rollback, concurrent exact retry, lost acknowledgement,
first-retained/raw-format identity and source/producer-join corruption. Test executor call counts
and forbid all upstream executor construction on operation/recovery paths. Add a neutral non-
procurement stage fixture. Validate installed package resources and actual CLI result semantics.

Full make check/coverage ratchets/package smoke/public challenges, exact legacy comparison,
latest-revision semantic evidence, one independent final architecture/semantic review, normal
protected delivery and installed main-pinned proof remain required before implementation closeout.
The existing policy/identity algorithms are not replaced; synthetic acceptance is integration and
policy-contract evidence, not enterprise approval validity, general ER quality or M4 completion.

## Review Focus for the implementation plan

1. Equal required quantities from distinct-content approved revisions retain every governing
   source path; identical-content recaptures cannot create extra authority.
2. A selected superseding revision omitting a predecessor item, including an empty successor,
   rejects before invoke and never yields a stale old requirement or manufactured zero.
3. Reordering selected producers/metadata and reformatting raw metadata never selects authority;
   raw audit identity remains separate from complete semantic computation identity.
4. Future approval, effectivity endpoints, timezone offsets, exact source scope versus derived
   governed scope, and mismatched catalogs cannot be hidden by value equality or newer ingestion.
5. Resealed metadata/projection/producer joins fail pure retained validation; one current seventh
   invocation never claims new upstream execution, invokes a missing upstream executor or bypasses
   explicit archive capability initialization.

## Next authorized work after approval

Create the bounded implementation Issue and write its executable plan before product edits. Pin
all public wire/type signatures, metadata field/nullability limits, aggregate budgets and receipt
projection, seven scenario dispositions and review focus. Preserve the approved inline method.
The current decision proposal and source profile/ADR do not themselves approve implementation.

## Builder check and explicit author calls for owner review

One fresh builder read this design and existing policy and raised two material ambiguities. This
proposal now chooses strict admission bounds for both, without changing policy v1:

1. An approved successor omitting an older item is unsupported when the selected supersession
   pair has different item sets. Cost: revision deletions/partial successor documents cannot use
   this first profile; a later coverage/deletion contract is required. Benefit: no stale predecessor
   quantity or fabricated zero can silently survive through a candidate-local policy adapter.
2. Identical source content hashes are duplicates regardless of declared revision/approval IDs.
   Cost: legitimate separately approved byte-identical revisions cannot be compared here. Benefit:
   repeated capture/relabeling cannot manufacture additional governing evidence. Equal-quantity
   joint governance remains supported for distinct-content revision documents.

Owner approval at `2c1b759` includes these explicit first-profile restrictions. No additional
independent review or policy implementation occurred. Schema layout, budget values within the
stated ceiling and delegated routine choices are frozen in the linked implementation plan,
which awaits owner review before product implementation.
