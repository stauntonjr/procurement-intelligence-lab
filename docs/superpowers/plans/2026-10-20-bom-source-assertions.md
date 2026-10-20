# BOM source assertion adoption

Issue #211; parent #33; ADR-037/022/017. Implement inline, with an independent whole-branch review.

1. Add failing platform contract and null-admission regression tests. Add immutable AssertionOrigin
   and SourceAssertionContext; extend SourceAssertion additively. Keep legacy IDs; validate rich
   evidence/value/provenance intrinsically. Add typed SourceAssertionError and C030 known-bad oracle.
2. Add failing BOM strategy tests and implement BomAssert over the existing AssertStrategy.
   Preserve one claim per observation, unresolved nulls, raw evidence and conflicting rows. Create
   mentions only from source SKU text. Use a per-run origin factory at explicit bootstrap wiring.
3. Add application and actual CLI tests, then implement --assertions (requires policy), fifth
   transformation, empty receipt, producer-output validation and deterministic per-claim traces.
   Preserve default three-stage and opt-in four-stage output. Prove in-memory append retention.
4. Add independent nine-source conformance and clean-wheel checks. Update adoption docs, README,
   ADR-022, milestone map and handoff. Seal code after focused tests and coverage-gap review.
5. Run unique-log make check/coverage, package smoke, all 30 oracles/known-bad mutations and
   conformance on one exact head. Obtain independent source/evidence review, publish validated
   semantic JSON and merge only with every required deterministic check green. Verify main CLI,
   tree equivalence and conformance; close only #211, retaining broader parents open.

Review focus: missing is not zero; unknown confidence is not a numeric score; no invented SKU
text/canonical key; conflicting claims and raw fields survive; context changes change rich IDs;
upstream event links cannot create an identity cycle; empty success requires a real receipt.

Read-only planning audit found no missing configured fields/labels/milestones/views. Project and
governing Issues were read directly. The latest post-merge Gemini audit failed HTTP 503 twice;
a new bounded audit was requested for this slice. Provider availability is not implementation
evidence and its report remains advisory. Known unrelated drift: #109's unchecked #112/#115 and
duplicate ADR-033 numbering; historical branch notes are explicitly superseded.

Review ruling: add an injected procurement output validator. Fresh review reproduced dropped,
partial, description-as-SKU and relabeled predicate outputs accepted by generic lineage checks.
Four failing producer tests pin the correction; core/application stays domain-neutral. This
strengthens the already specified producer-output boundary without expanding business policy.
