# Issue118 — state-construction invariant evidence

Binding contract: Issue118, ADR020 and the approved existing expected/observed semantics.
Baseline main9818d09; candidate runtime source0564d705903a67fd61c690ee83eb9f4eb48ab58c.
The only product behavior change rejects timestamps whose tzinfo exists but supplies no UTC offset,
using existing ValueError-compatible TemporalContractError at the two constructors/two helpers.

- baseline.log:13 existing state/governed-state tests pass.
- offsetless-red.log:4 expected DID NOT RAISE failures before the source fix.
- focused-green.log:83 checks pass, including quantity properties and all four public boundaries.
- installed-probe.py / installed.json:77 copied public API/property cases pass outside checkout against
  a clean installed wheel, zero failures/skips; exact test-source pins, package path, argv and wheel hash.
- challenges.json / challenges.log:31 public oracles pass and31 known-bad equivalents reject.
  C008 remains unchanged; C031 protects actual UTC-offset awareness. No agent-quality score.
- package-smoke.log:clean installation and advertised commands with task-owned real Postgres pass.
- planning-audit-before.json:129 items/25 fields/11 views; no missing configured objects.
- semantic-change.json:seven scenario families and reviewed31c1ff0 qualification contract; ready for protected delivery.
- check.log / qualification.json:1956 passed/22 explicit browser-live skips, zero storage skips; unchanged ratchets.
- independent-review.md / progress.md:exact single review, no findings, all declined boundaries/costs.
- focused-challenges.json is the initial precommit working-tree checkpoint (annotated); challenges.json is the final source-pinned report.

Source quantities/evidence/key/scope, distinct record times, valid offsets, zero/fractions/overages,
partial/missing observations, governing policy and outstanding arithmetic retain existing semantics.
There is no production, enterprise authority, aggregation, job or broader M4 acceptance claim.
Full suite and the single independent review pass. Actual protected PR/main-installed acceptance, Issue/Project closure and terminal cleanup are retained in Issue118; this directory pins branch qualification.

Pre-slice hosted advisory40202523349 on main9818d09 failed GeminiHTTP503 (81-file snapshot
 a4b9bb1758e2edb68919ff9c7b41371167ec0d54fbe5fa934160590ac7f53cf1).
This is provider availability, not completed roadmap evidence; direct Issue/ADR/source/Project
review and the structural audit are separate. No silent provider substitution was made.
