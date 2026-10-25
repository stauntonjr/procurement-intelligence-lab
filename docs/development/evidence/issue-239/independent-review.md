# Independent architecture and semantic review

Reviewed range: `a8de65db7ae6b6192a937ae930859d1b205be5aa..1ec30d23817d92dd56b75698610ea23693bbe990`.
Reviewer: one fresh-context `gpt-6-astra` agent, high reasoning, no subagents or mutations.
This is the agreed single whole-branch review. The reviewer confirmed unchanged HEAD/clean tree.
The following records observable findings and verification, not private reasoning.

## Important finding: wrong domain/profile reaches storage and invocation

P2 / Important. RetainedReconciliationService.preflight checks RECONCILE binding and descriptor,
but supported procurement domain/source-profile validation occurs only in completed-result
validation (application/retained_reconciliation.py:94 and bootstrap.py:1074 at reviewed revision).

Changing only manifest domain.id to inventory preserved valid binding/registry/config/producers.
Independent service reproduction accepted preflight, constructed the executor, invoked RECONCILE,
then returned pil.interpretation.package_execution_contract_invalid. Actual CLI reproduction
with unavailable storage returned pil.infrastructure.archive_unavailable, masking invalid input.
The approved design and Tasks3/6 require invalid deployment rejection before storage/invocation.

Safe correction: apply the existing procurement domain and dedicated source-profile ID/version
predicate in pure bootstrap admission before either archive factory or executor construction;
reuse it in retained validation. Preserve neutral non-procurement conformance. Cover append and
nonappend callers, unavailable storage and forbidden executor construction. No broader future-stage
manifest-policy defect was reproduced; this finding authorizes no new future-stage policy.

Verdict at reviewed revision: request changes for this single Important finding. No optional minors.
Completion remains unapproved until the finding, full deterministic checks/coverage, evidence,
protected delivery and main-pinned proof are resolved.

## Inspected contracts

All five plan Review Focus areas otherwise align: equal distinct-content sources retain every
path and identical content rejects; selected successor item sets must match; ordering/raw JSON
never choose authority; approval/effectivity/offsets/source-derived scopes/catalogs stay explicit;
retained metadata/projections/joins revalidate and recovery constructs no upstream executor.

The reviewer inspected domain bridge, neutral contracts/runner, explicit bootstrap, public callers,
finite codec registration, immutable joins/transactions/concurrency/retry, recovery/export, changed
tests, installed probe/corpus, legacy comparison and retained receipts. Dependency direction is
sound and no model/algorithm replacement was identified.

## Independently executed verification

- Six semantic/authority/runner/codec/admission suites:49 passed in8.70s.
- Real-Postgres archive/publication contracts plus archive CLI suite:24 passed in47.22s,
  including concurrency, rollback, lost acknowledgement, corruption and source-free recovery/export.
- Architecture import and whitespace checks: passed.
- Both wrong-domain counterexamples above: reproduced.
- src/pyproject.toml/uv.lock comparison to wheel-qualified4d969ef: unchanged.

The reviewer inspected rather than reran public127 compatibility, clean base3.12/3.13 probes,
storage17-case corpus, legacy22-operation equality, package-smoke and30 challenge receipts.
These remain bounded synthetic qualification evidence.

## Declined to judge as findings

1. Missing operation digest after ambiguous acknowledgement: approved errors contain known scope
   and producer recovery identities; documented scoped history/exact-pin retry is sufficient.
   The lost-acknowledgement contract passed.
2. Duplicate-content/repeated-row rejection and equal supersession item sets: explicit approved
   first-profile restrictions.
3. Outside-selected supersession references and historical as-of before ingestion: explicitly
   supported, without global completeness or ingestion-based authority.
4. Separate companion source exports: result export truthfully declares that source bytes are separate.
5. Independent node-limit measurement testing: reasonable recorded ruling with actual public byte
   coverage; not isolated public-node-limit proof.
6. Clone restoration/static validation/final receipt callbacks: reasonable ledgered choices;
   missing domain/profile admission remains the Important finding.
7. Coherent arbitrary rewriting by database owner: outside documented authenticity boundary;
   ordinary-write immutability/detectable broken joins remain covered.
8. Broader expected/observed invariants, human reconciliation, aggregation, fresh seven-stage flow,
   jobs, DERIVE/ACT, enterprise approval and production quality: explicitly deferred without claim.
9. Pending full qualification and stale single-profile test: acceptance/test maintenance status,
   not additional fabricated product defects.
