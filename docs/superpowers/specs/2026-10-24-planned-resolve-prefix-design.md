# Explicit planned RESOLVE prefix and retained identity evidence

Status: owner-approved on 2026-10-24 at written proposal revision
`052ab479116fa35704cb3a5f970f89d19b337bea`; the owner instructed proceed with implementation
planning. Decision [#235](https://github.com/stauntonjr/procurement-intelligence-lab/issues/235),
primary M3, parent #14; accepted ADR-046. No implementation or runtime acceptance is claimed.

## Intent and current boundary

Extend actual planned procurement execution from INGEST-through-ASSERT to
INGEST-through-RESOLVE. A trusted local developer supplies a synthetic, scoped catalog of
canonical internal SKU keys. Every actual source mention receives an explicit identity outcome,
including abstention, tied to its original row evidence and the exact candidate snapshot.
Retain the completed six-stage computation durably without changing source claims or promoting
identity into governing state. This advances package adoption after the delivered local jobs.

Baseline main is `88d32d4f5da0f5cae500d465f80173b213ee71d0`. ADR-022 owns the fixed topology.
ADR-043/044/045 and #226/#229/#232 deliver the five-stage executor, completed-prefix archive and
local jobs. Their existing public payloads, identities, explicit initialization and recovery
contracts remain supported. Issues #14/#42/#39/#43/#45 govern identity and evaluation; #36
retains broader ingestion work. This slice completes none of those broad Issues.

The real ASSERT adapter emits row-grounded `procurement_item` mentions. The existing
`resolve_identifier` uses casefold plus alphanumeric filtering and accepts exactly one matching
candidate. Its evidence lookup compares assertion subject text with mention text; the adopted
ASSERT path uses row identities instead. Reusing that lookup would lose evidence. The new
adapter reuses the matching rule and explicitly obtains evidence from the exact mention row.

## Approaches and author calls

The owner chose RESOLVE over further listener/worker work. Within that direction, an explicit
six-stage profile is the bounded approach: use the same planner and actual first-five runner,
then one registered RESOLVE executor, with new typed output/receipt/archive contracts.
Silently widening the delivered five-stage job/snapshot types would invalidate their pinned
wire, codec and attempt contracts. A standalone legacy resolver helper would not establish
actual planned execution or durable provenance. Full RECONCILE/state adoption would add a
separate authority decision. Those alternatives are outside this proposal.

Approved author calls: internal SKU keys only in one exact scope; a complete explicit local
candidate snapshot with no aliases; unchanged normalized-exact matching; a new opt-in six-stage
caller and archive capability; original five-stage jobs remain five-stage. No new framework,
external dependency, model, provider or scoring algorithm is proposed.

## Goals, non-goals and anti-goals

Goals are a real sixth invocation, positively validated row/evidence lineage, reproducible input
identity, truthful empty/absent/unresolved states, scoped source-free recovery, and legacy
compatibility. A six-stage result still reports package completion false.

No RECONCILE/DERIVE/DETECT/PREDICT/DECIDE/ACT execution; global catalog or canonical entity
creation; manufacturer/vendor identifier equivalence; aliases/substitutions; fuzzy ranking,
probability or confidence estimate; entity-review workflow; automatic correction replay;
six-stage durable jobs; listener/queue/worker/lease; operational-agent permission; authenticated
production service; browser/live-model or production deployment. Source-local SKU equality is
not a claim of real-world entity identity beyond the explicitly declared catalog boundary.

Never infer candidates from the same document's observed SKU list, treat a catalog file as
independently verified truth, collapse duplicate source rows, discard losing candidates, turn a
missing catalog into an empty catalog, or claim that normalized exact matching satisfies M3's
full benchmark/namespace/review criteria.

## Authoritative input, scope and policy

Inputs are the compiled package, complete descriptor registry/config, explicit source/context,
normalization policy, a `BomResolutionPolicy` instance, and a bounded candidate-snapshot JSON
file. No ambient catalog, provider lookup or runtime fallback is permitted.

`CandidateSnapshot` is an immutable platform input with schema/version, declared catalog ID and
revision, exact four-part `StateScope`, entity type, identifier namespace, timezone-aware
effective/as-of time, and a tuple of candidate keys. This profile supports only
`procurement_item` / `internal_sku`; each candidate's raw internal-SKU key is also its returned
canonical key. These are caller-declared local catalog identities, not a new global entity table.
The policy explicitly asserts that this source profile's SKU column and the supplied catalog
use that same namespace. Unsupported namespace/type/policy combinations fail before source I/O.

The catalog scope must equal the source scope including version. Resolution as-of is the pinned
execution capture/start time. Source observation and catalog effective time must be <= as-of;
no future entry or implicit latest-version selection. A catalog revision is a label, not an
independent freshness attestation. No staleness duration is invented: use exactly the admitted
snapshot, expose its time, and make no current/freshness claim.

The strict boundary rejects absent/unknown/duplicate JSON fields, invalid UTF-8/Unicode,
non-finite values, mutable values and wrong scalar types. Bound candidate JSON at 32KiB,
256 keys and 256 Unicode characters per key. Keys must be nonblank and normalize to a nonempty
identifier. Exact duplicate raw keys are malformed; distinct keys with the same normalized
form remain separate candidates and cause ambiguity. Empty keys tuple is valid positive evidence
of an explicitly supplied empty catalog. An absent snapshot is a typed admission failure.

Canonical snapshot identity includes every declared field and exact raw keys in canonical
lexical order. Formatting and input order do not change semantic content identity. Retain the
original bounded JSON bytes and their SHA256 separately for audit; raw formatting is not an
algorithm input. Both canonical and raw identities are visible in the retained result.

`BomResolutionPolicy` has an explicit version/content identity and declares namespace, entity
type, normalization rule and unique-match/abstention semantics. Resolve the existing
`procurement.resolve/normalized-exact@1` declaration to its exact instance/hash. Candidate data
is a separate execution input, never disguised as policy or selected from a declaration label.

## Matching, evidence and output

For each admitted `EntityMention` in original ASSERT order:

1. Require the exact source scope, observation time and supported type; all assertion objects
   must be exact members of the preceding ASSERT output and the single source row.
2. Require exactly one evidenced HAS_SKU claim whose non-null raw value equals mention text.
   Obtain that claim from the mention; do not search other rows by normalized subject text.
3. Apply the unchanged legacy normalized-exact rule against the complete canonical key tuple.
   Exactly one normalized match resolves to that raw key. Zero matches or multiple distinct
   matches produce UNRESOLVED and an explicit no-match/ambiguous reason. A nonblank source
   mention that normalizes to empty abstains with an invalid-identifier reason, never an empty
   key match. Do not invent a numeric score or threshold.
4. Produce an immutable `MentionResolution` linking mention ID, legacy-shaped
   `ResolutionDecision`, full snapshot identity, matched keys, policy and provenance. The
   decision evidence is the exact HAS_SKU claim from that mention row. Keep all candidates in
   the shared retained snapshot; never replace the snapshot by winners alone.
5. Only a resolved outcome permits `CanonicalizedAssertion` links for the exact claims already
   belonging to that mention row. They retain original values, original IDs and evidence,
   resolution ID, exact scope and effective time. No claim from another row may be linked,
   even if subject text or normalized SKU agrees. Unknown values remain unknown.

`ResolvedOutput` retains the exact preceding `AssertedOutput`, complete candidate snapshot,
policy, one outcome per mention, canonicalized assertion links and explicitly unlinked source
assertion IDs. A source row with absent/null/blank SKU has no mention under existing ASSERT
semantics; its source claims remain unlinked and visible. It is not silently counted as resolved
or emitted as a fabricated mention. Duplicate rows/mention texts remain separate evidence.

Independent platform and domain validators check one-to-one mention coverage, no duplicate
outcomes or cross-row/scope/value substitution, exact candidate membership/matching dispositions,
and exhaustive disjoint linked/unlinked source membership. An evidenced zero-row document has
zero mentions/outcomes/links, all six actual invocations and a real resolution batch ID/event;
an empty tuple is not proof of a missing sixth invocation.

The RESOLVE transformation event uses the ASSERT batch/event, exact mention/claim identities,
candidate content ID and policy instance as inputs. Its output IDs include a batch ID even when
empty, mention-outcome IDs, decision IDs and canonical-link IDs. Provenance retains the real
registered implementation/version, pinned context and those inputs. It must not form a hash
cycle with its own output, receipt or completion timestamp. Candidate/policy changes affect
sixth-stage identities without rewriting the retained original claims.

## Runtime, ownership and receipts

Platform owns candidate snapshot/mention-outcome transport, sixth-stage output/receipt validation,
admission and execution mechanics without importing procurement. Procurement owns the supported
namespace/profile policy and normalized-exact strategy adapter. Bootstrap explicitly injects
catalog, policy, registered executor, store and clock. Input files never cause arbitrary imports,
domain-name branching or provider selection.

Add separate six-stage request/prepared/receipt types rather than weaken ASSERT-only constructors.
The same validated planner retains all twelve declarations. The new profile admits actual
compatible registrations for stages 1-6 and all declared reference/version/settings requirements
before opening the source. Later planning-only descriptors remain metadata. In-prefix neutral
modes, wider stop boundaries and wrong executor metadata reject before source I/O.

Invoke each real strategy once: reuse the existing first-five preparation/runner, retain its
exact `PrefixExecutionReceipt` as an embedded prefix, and then invoke RESOLVE on that exact
output. This is not a second execution or a rerun of the legacy pipeline. The first-five receipt
remains ASSERT-only. The new outer `ResolvedPrefixExecutionReceipt` proves six-stage completion,
contains twelve ordered entries (first five copied, sixth actual, final six NOT_EXECUTED), and
retains the full plan, catalog, policy and sixth-stage event/output.

The six-stage computation digest binds the embedded five-stage computation digest, full plan,
candidate semantic content, policy/registration/context and actual sixth output. Completion
times and candidate raw-file checksum belong to receipt/audit identity, not matching computation
identity. Preserve the first-five independent receipt and sample a final completion clock after
validated RESOLVE output; final time cannot precede prefix completion or the initial server
sample. `requested_prefix_complete=true` and `package_execution_complete=false` never imply
every mention resolved, governing state constructed or the catalog externally authoritative.

## Durable retention and recovery

Add explicit `planned_resolution_prefix/v1` capability beside existing archive capabilities,
with neutral `ResolvedExecutionArchive` port and Postgres adapter. Initialization is explicit;
no ordinary run/read implicitly changes schema. Require the existing source/assertion and
completed-prefix archive capabilities and initialize only additive tables/markers. No migration,
reinterpretation or deletion of existing v1 rows/payloads is allowed.

Publish captured source bytes, unchanged five-stage DocumentSnapshot/prefix computation,
candidate raw/canonical data and six-stage computation/receipt in one database transaction.
Validate all content, type, lineage and policy identities before publication. The existing source
snapshot retains exactly its five transformations so legacy source readers still agree.
Do not call the existing standalone append API and commit the five-stage result before the
six-stage transaction. Share adapter transaction mechanics through an explicit composed path.

The retention key is exact scope plus six-stage computation digest. Exact repeat computations
preserve the first retained complete receipt; return the current invocation receipt separately.
Concurrent same computations converge on the same retained identity; incompatible content under
an existing identity is integrity/conflict failure, never overwrite. Different catalog/policy
snapshots create different computations. No lookup-before-execution shortcut or result cache.

An acknowledgement loss may follow successful commit; the error must not imply rollback.
Scoped show/history/content/export verifies the full stored graph without source files,
candidate files, current config or installed executors. Absence/foreign scope is not-found;
bad stored content/digests/joins are integrity failures. History retains bounded sequence cursor
semantics without inferred totals; export is atomic and refuses overwrite. Preserve existing
16MiB / 50,000-node / depth64 allowlist-codec bounds and exact old snapshot encodings. Oversized
new graphs fail with a typed bound/contract error and publish no result. Ordinary SQL write
guards follow the existing trusted local boundary; owner bypass remains outside it.

No local_prefix_jobs/v1 record may contain this new request/receipt. Existing submit/run/retry/
abandon/result commands and frozen stored-input validation retain their exact five-stage meaning.
Job adoption of the new profile requires a separate explicit contract and follow-up Issue.

## Public caller and typed failures

Add explicit installed `python -m procurement_intelligence_lab.interfaces.execute_resolved_package`
with source, manifest, registry, config, context, normalization-policy, resolution-policy,
candidate-snapshot and required `--stop-after RESOLVE`; optional `--archive` selects the new
capability. New resolution-archive init/show/history/content/export commands are scoped and
separate from existing readers. Runtime fixtures must advertise an actual sixth executor.
No hidden checkout paths or packaged default catalog; all source/candidate data are synthetic.

Return source/five-stage payload, candidate identity/data, every outcome/abstention, canonical
links/unlinked IDs, actual sixth event and outer receipt. Archive mode additionally returns first
retained versus current receipts. Recovered export contains sufficient pinned inputs to inspect
the historical decision without rerunning current code.

Reuse existing planning/input/execution/output-contract/archive-not-ready/unavailable/not-found/
conflict/integrity error families with sanitized stable codes and exit2, JSON stderr, no partial
success stdout, traceback, DSN or settings values. Candidate/policy/scope/time/namespace errors
are preflight input failures; a valid unmatched/ambiguous mention is a successful abstaining
outcome, not an exception. A bad invoked sixth output is an interpretation/contract failure.
Stage or storage failure cannot publish a completed-six-stage receipt; transactional rollback
also prevents a new source/prefix/catalog row. No rollback of arbitrary external side effects
or exactly-once process execution is claimed.

## Acceptance and scenario dispositions

All families are applicable; latest implementation evidence must be recorded against the exact
source revision using the semantic-change schema. Proposed oracles are requirements, not results.

| Family | Required oracle |
|---|---|
| Empty/missing/unknown | Zero rows, no mentions, supplied empty catalog, absent catalog, null/blank/unmapped SKU, nonempty invalid-normalized mention; distinguish actual empty batch from missing invocation |
| One/many/duplicate/conflict | Unique match, no match, normalized collision, repeated row/SKU, exact catalog duplicate rejection, same mention text across rows, complete candidate retention and exact row coverage |
| Scope/time/as-of | All four scope fields and entity/namespace isolation; future source/catalog rejection, equal timestamp boundary, older pinned snapshot, offsets, catalog-version/content substitution |
| Numeric/boundaries | Preserve zero/negative/fractional quantity and exact monetary values without interpreting them as identity; 0/1/256/257 catalog keys, key/JSON/graph size and timestamp limits |
| Unsupported/malformed | Duplicate/unknown JSON, nonfinite/Unicode/bool values, wrong snapshot/policy/version/executor, neutral sixth mode, later-stage request; reject before intentionally absent source |
| Public/artifact | Real subprocess six-stage invocation plus archive/restart/show/history/export after original source/catalog/config deletion; fresh clean base/storage wheels outside checkout; SQL concurrency/rollback/acknowledgement loss |
| Safe counterexample | Preserve all ASSERT-only JSON/digest/codec/job/review/replay paths; no candidate inferred from source; unresolved result never canonicalized; no fake score/governed state; non-procurement executable fixture follows neutral platform path |

Add a small synthetic, hash-pinned resolution integration corpus with raw source row, complete
candidate snapshot and expected outcome for every case. Compare matching outcomes against the
unchanged legacy normalized-exact rule, separating evidence-binding repairs from algorithm
changes. Report precision/recall/false merges/abstention and counts/denominators only for this
bounded declared-namespace corpus; distinguish observed zero errors from an unsupported safety
claim. Keep matched candidates and source examples for every error. No general ER benchmark,
domain-quality, production identity or #45 completion claim follows. An algorithm change needs
a separate decision and comparable benchmark manifest.

Implementation qualification requires focused RED/GREEN public/contract tests, full `make check`
and coverage ratchet, all existing challenges and regression challenges for any shipped defect,
clean artifact probes, one independent final architecture/semantic review with findings resolved,
required deterministic protected checks, and an exact merged-main installed proof. A passing
helper or draft spec is not acceptance. Preserve Native/inline execution and the established one
independent final review method; do not silently multiply review loops.

## Delivery sequence and approval record

One fresh-context builder check of proposal `052ab47` reported "nothing important left".
The owner approved that written document on 2026-10-24 and instructed proceed. This authorizes
implementation planning; the resulting plan must be reviewed before product implementation.
Create the smallest implementation Issue under #14, use writing-plans, then implement
contracts, real strategy/runtime, atomic archive, actual public caller and exact-revision evidence
as a single bounded vertical slice. Decision #235's durable acceptance and implementation
delivery remain separate. No new production or model spend is authorized here.

Orientation: exact-main hosted advisory40115378490 failed Gemini HTTP503 (one request,77 files,
snapshot `a5829e51b4d32fded2c5ec91e7a0eab5ddd95bc66336e1bb818ae996f91388b2`); no report.
Direct docs/code/Issue/Project review and structural audit are separate evidence. ADR033 numbering
and historical demo-priority wording remain unrelated drift. Parent #36's stale plan-pending
summary is corrected to the delivered #232 boundary; original broader acceptance stays open.
