# Universal logical-stage semantics

Status: implementation contract for [Issue #151](https://github.com/stauntonjr/procurement-intelligence-lab/issues/151).

## Meaning of complete

The universal logical pipeline is **semantically complete** when every stage has:

1. a concrete, framework-independent input and output type;
2. intrinsic validation for missing, scope, time, evidence, and state distinctions;
3. a `Protocol` describing executable strategy behavior without placing callbacks in a
   `DomainPackage`;
4. a registered contract name checked against the stage catalog; and
5. an explicit typed `EMPTY` meaning distinct from failure, unknown, unresolved, or skipped work.

Semantic completeness does not mean every vertical executes every stage. Procurement forecasting,
decision policy, and external actions remain absent. Its future package may bind those stages to
typed `EMPTY` modes until separately implemented and evaluated.

## Contract map

| Stage | Input | Output | Adjacent explicit contracts | Runtime strategy |
|---|---|---|---|---|
| INGEST | `SourceReference` | `Artifact` | immutable capture identity | `IngestStrategy` |
| STRUCTURE | `Artifact` | `StructuredDocument` | `StructuredElement` | `StructureStrategy` |
| MAP | `StructuredDocument` | `MappedDocument` | `MappedField` | `MapStrategy` |
| NORMALIZE | `MappedDocument` | `NormalizedObservation` | diagnostics, unit, epistemic status | `NormalizeStrategy` |
| ASSERT | `NormalizedObservation` | `SourceAssertion` | `EntityMention` | `AssertStrategy` |
| RESOLVE | `SourceAssertion` | `ResolutionDecision` | `CanonicalizedAssertion`; abstention | `ResolveStrategy` |
| RECONCILE | `CanonicalizedAssertion` | `OperationalState` | `ReconciliationDecision`, governing and losing claims | `ReconcileStrategy` |
| DERIVE | `OperationalState` | `DerivedFact` | source-state and evidence links | `DeriveStrategy` |
| DETECT | `OperationalState` | `Anomaly` | typed details, lifecycle, policy and scope | `DetectStrategy` |
| PREDICT | `EvidenceAndState` | `Prediction` | bounded confidence, horizon, uncertainty basis | `PredictStrategy` |
| DECIDE | `FactsAnomaliesPredictions` | `Decision` | scoped `DecisionAuthority` | `DecideStrategy` |
| ACT | `ApprovedDecision` | `ActionResult` | `ActionApproval`, idempotency and terminal-state rules | `ActStrategy` |

`platform/domain_packages/contract_registry.py` is the executable bridge between the
language-neutral names above and their Python contracts. Importing or compiling a package fails if
a catalog name has no same-named concrete registration, appears more than once, or drifts from the
registered type name. This does not place Python types in the compiled manifest, so schema 1.0 JSON
and its deterministic hash remain stable.

## Invariants and truth table

| Scenario family | Required behavior | Executable evidence |
|---|---|---|
| Empty | No logical records is the typed stage-empty result; an empty artifact or document remains an explicit captured record | empty document contracts and existing DomainPackage neutral-mode tests |
| Missing / unknown / unresolved | `None` requires an unresolved status and diagnostic where a value is expected; it never becomes numeric zero or a resolved value | mapped/normalized/state tests |
| One / many / duplicate / conflict | Multiple records are allowed; duplicate semantic keys fail; reconciliation retains governing and losing assertions | structure, mapping, reconciliation and state tests |
| Scope / cross-scope | Durable records carry `StateScope`; prediction and decision composition rejects mismatched or absent scope | prediction and decision input tests |
| Stale / future / as-of | Semantic timestamps are timezone-aware; inputs newer than an aggregation `as_of` fail | artifact, prediction, decision, approval and action tests |
| Zero / negative / fractional / boundary | Zero and fractions remain values; non-finite decimals fail; probability accepts exactly 0 and 1 and rejects values outside the closed interval | Hypothesis confidence property and numeric tests |
| Evidence | Structure, mapping, state, derivation, prediction, decision, approval and action results retain source evidence | complete inventory topology fixture |
| Authority / side effects | A recommendation is not approval; only explicitly action-authorized, scoped approval can produce an attempted action result | action authority tests |
| Idempotency / result state | Every action result has a non-empty key; attempted, succeeded and failed states have distinct completion/failure rules | action status tests |
| Safe counterexample | An inventory fixture uses the entire platform topology without importing procurement | `test_non_procurement_fixture_exercises_every_typed_stage_contract` |

## Operational status

The semantic contracts are reusable definitions, not claims of deployed capability:

- the current XLSX procurement path still combines STRUCTURE and MAP physically;
- existing procurement behavior executes through DETECT with the limitations documented in the
  procurement semantic model;
- no procurement `DomainPackage` is yet wired to the runtime;
- PREDICT, DECIDE, and ACT have no procurement executors or policies;
- the runtime capability registry and logical-to-physical planner remain future work; and
- a second production vertical remains an M9 proof, while the inventory fixture is only a
  portability counterexample.

Requiring scope at DETECT intentionally extends anomaly semantic identity: `anomaly_id` now includes
`StateScope`. Identical subject/value/evidence combinations in different tenants, projects, sites,
or state versions no longer collide. This is a deliberate identity correction rather than a
DomainPackage manifest-schema change.

Prediction and decision inputs have stable aggregate identities. `Prediction` retains the exact
`EvidenceAndState.input_id`, and `Decision.decision_id` incorporates its exact fact, anomaly, and
prediction bundle. Artifact identity likewise includes capture time and capture provenance, so a
re-capture is not silently conflated with the earlier event.
