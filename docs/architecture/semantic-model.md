# Shared semantic vocabulary

This glossary indexes the accepted semantics for [Issue #20](https://github.com/stauntonjr/procurement-intelligence-lab/issues/20).
It consolidates ADR-003, ADR-022 and the existing typed contracts; it introduces no new policy,
enum value, stage, or execution capability. The [procurement model](../domains/procurement/semantic-model.md)
specializes these concepts. [Platform ownership](platform-semantics.md) and the
[logical-stage contract map](universal-stage-semantics.md) define their reusable boundaries.

## Order and boundaries

```text
Artifact → StructuredDocument → MappedDocument → NormalizedObservation
→ SourceAssertion → EntityMention → ResolutionDecision → CanonicalizedAssertion
→ ReconciliationDecision → OperationalState → DerivedFact → Anomaly
→ Prediction → Decision → approved action → ActionResult
```

This is conceptual order, not a requirement that every adjacent record be a separate task or
that every later stage consume only the immediately preceding output. ASSERT produces claims
and mentions; RESOLVE records identity decisions and successful canonicalization; RECONCILE
records governing-claim decisions and state. DETECT can inspect state; PREDICT accepts evidence
and state; DECIDE accepts facts, anomalies and predictions. The platform-owned schedulable order
remains `INGEST → STRUCTURE → MAP → NORMALIZE → ASSERT → RESOLVE → RECONCILE → DERIVE → DETECT → PREDICT → DECIDE → ACT`.
The [catalog](../../src/procurement_intelligence_lab/platform/domain_packages/package.py),
[contract registry](../../src/procurement_intelligence_lab/platform/domain_packages/contract_registry.py)
and ADR-022 govern that topology. Physical fusion, explicit neutral modes and provenance graph
branches do not grant a domain authority to reorder it.

## Glossary and governing work

Each source link names the existing Python contract, not a claim of full procurement adoption.
The linked Issues retain their own acceptance criteria and delivery status.

| Concept / contract | Meaning and retained evidence | Governing Issue contracts |
|---|---|---|
| [Artifact](../../src/procurement_intelligence_lab/platform/semantics/artifacts.py) | Immutable capture boundary: source reference/scope/version, content hash, media type, byte length, capture time and execution provenance. Capturing bytes does not approve their claims. | [#29](https://github.com/stauntonjr/procurement-intelligence-lab/issues/29), [#36](https://github.com/stauntonjr/procurement-intelligence-lab/issues/36) |
| [StructuredDocument](../../src/procurement_intelligence_lab/platform/semantics/documents.py) | Located elements and ordering recovered from an artifact, retaining artifact identity, element EvidenceRefs and transformation provenance. Structure describes what was found before domain schema assignment. | [#30](https://github.com/stauntonjr/procurement-intelligence-lab/issues/30) |
| [MappedDocument](../../src/procurement_intelligence_lab/platform/semantics/documents.py) | Fields interpreted under a named mapping schema, retaining the structured document, raw values, source locations, epistemic status and missing-value diagnostics. Mapping is distinct from normalization. | [#32](https://github.com/stauntonjr/procurement-intelligence-lab/issues/32) |
| [NormalizedObservation](../../src/procurement_intelligence_lab/platform/semantics/observations.py) | Comparable typed value/unit for a predicate and subject hint, retaining the source field, scope, effective time, status, diagnostics and provenance. Comparable values still make no identity or authority decision. | [#31](https://github.com/stauntonjr/procurement-intelligence-lab/issues/31) |
| [SourceAssertion](../../src/procurement_intelligence_lab/platform/semantics/assertions.py) | A source's predicate/value claim with evidence, not truth. The provenance-complete path retains normalization context, artifact/origin, method/component provenance, confidence diagnostic and recording time. Legacy context-free assertions remain a separate compatibility path. | [#33](https://github.com/stauntonjr/procurement-intelligence-lab/issues/33), [#37](https://github.com/stauntonjr/procurement-intelligence-lab/issues/37) |
| [EntityMention](../../src/procurement_intelligence_lab/platform/semantics/resolution.py) | A source-grounded surface form and entity type tied to assertions, scope and observation time. A mention is not a canonical entity; unresolved identity remains inspectable. | [#42](https://github.com/stauntonjr/procurement-intelligence-lab/issues/42) |
| [ResolutionDecision](../../src/procurement_intelligence_lab/platform/semantics/resolution.py) | An explicit identity decision with rationale, supporting assertions and decision provenance. The current shared envelope is RESOLVED or UNRESOLVED; unresolved decisions carry no canonical key. Broader scoring/review outcomes are not additional implemented enum values. | [#42](https://github.com/stauntonjr/procurement-intelligence-lab/issues/42), [#43](https://github.com/stauntonjr/procurement-intelligence-lab/issues/43), [#45](https://github.com/stauntonjr/procurement-intelligence-lab/issues/45) |
| [CanonicalizedAssertion](../../src/procurement_intelligence_lab/platform/semantics/resolution.py) | A source assertion linked to a successful resolution decision, canonical key, scope and effective time. Identity association preserves the original claim; it does not make the value governing. | [#42](https://github.com/stauntonjr/procurement-intelligence-lab/issues/42), [#46](https://github.com/stauntonjr/procurement-intelligence-lab/issues/46) |
| [ReconciliationDecision](../../src/procurement_intelligence_lab/platform/semantics/reconciliation.py) | A policy-identified selection/disposition of canonicalized claims, with governing and losing claims, rationale, status and provenance. Procurement's predicate-specific policy further retains eligibility, approval/effective-time and conflict dispositions. | [#46](https://github.com/stauntonjr/procurement-intelligence-lab/issues/46), [#239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239) |
| [OperationalState](../../src/procurement_intelligence_lab/platform/semantics/state.py) | A governed projection for a subject, versioned scope and as-of time, with attribute values/status, freshness, evidence and decision provenance. It does not replace assertion history. Procurement keeps expected requirements and observed procurement separate. | [#47](https://github.com/stauntonjr/procurement-intelligence-lab/issues/47), [#118](https://github.com/stauntonjr/procurement-intelligence-lab/issues/118) |
| [DerivedFact](../../src/procurement_intelligence_lab/platform/semantics/derivation.py) | A deterministic calculation from identified operational states, retaining scope/as-of, evidence, units and calculation provenance. Its status is INFERRED; deterministic arithmetic does not turn it into a direct source observation. | [#48](https://github.com/stauntonjr/procurement-intelligence-lab/issues/48), [#49](https://github.com/stauntonjr/procurement-intelligence-lab/issues/49) |
| [Anomaly](../../src/procurement_intelligence_lab/platform/semantics/anomalies.py) | An evidence-backed, scoped assessment under explicit detection semantics, with typed details, severity and lifecycle. A discrepancy or unresolved-identity assessment is distinct from a forecast or authorization to act. | [#60](https://github.com/stauntonjr/procurement-intelligence-lab/issues/60) |
| [Prediction](../../src/procurement_intelligence_lab/platform/semantics/prediction.py) | An uncertain outcome with horizon, as-of/scope, input bundle, evidence, confidence, uncertainty basis and model/execution provenance. It is not an observed state or a delivery commitment. | [#61](https://github.com/stauntonjr/procurement-intelligence-lab/issues/61), [#64](https://github.com/stauntonjr/procurement-intelligence-lab/issues/64) |
| [Decision](../../src/procurement_intelligence_lab/platform/semantics/decisions.py) | A policy-backed recommendation, deferral or rejection over a scoped facts/anomalies/predictions bundle, retaining authority identity, rationale, evidence and provenance. A recommendation alone grants no action approval. | [#65](https://github.com/stauntonjr/procurement-intelligence-lab/issues/65), [#67](https://github.com/stauntonjr/procurement-intelligence-lab/issues/67) |
| [ActionApproval / ApprovedDecision](../../src/procurement_intelligence_lab/platform/semantics/actions.py) | Approval of the exact recommended decision by authority explicitly permitted to approve actions, with matching scope, approval time and evidence. Development-agent approval and operational action authority remain separate. | [#67](https://github.com/stauntonjr/procurement-intelligence-lab/issues/67) |
| [ActionResult](../../src/procurement_intelligence_lab/platform/semantics/actions.py) | Audit record for an approved action: kind, idempotency key, attempted/succeeded/failed status, timestamps, evidence, provenance and applicable failure/external reference. An attempt is not completion; a typed contract is not an enabled external integration. | [#68](https://github.com/stauntonjr/procurement-intelligence-lab/issues/68) |

## Evidence, uncertainty and authority

[EvidenceRef](../../src/procurement_intelligence_lab/platform/semantics/evidence.py) identifies the
supporting source/location. Transformation events record how outputs were produced; decision
provenance records the component/policy execution context. Stable identity does not imply approval,
correctness, freshness or completeness. Later layers preserve links to their inputs and the
inputs' epistemic context; they need not copy one status field unchanged through every layer.
The shared [EpistemicStatus](../../src/procurement_intelligence_lab/platform/semantics/epistemics.py)
values are OBSERVED, INFERRED and UNRESOLVED. An observed source claim can still conflict with
another claim. Dispute, review, resolution, reconciliation and freshness have their own records
or dispositions; they are not synonyms for epistemic status. [#35](https://github.com/stauntonjr/procurement-intelligence-lab/issues/35)
and [#40](https://github.com/stauntonjr/procurement-intelligence-lab/issues/40) govern the broader
trace and typed-confidence work. Heterogeneous model, retrieval and identity scores do not form
an aggregate authority score.

Unknown observation, unresolved identity, conflicting authority, intentionally EMPTY stage and
NOT_EXECUTED stage are distinct states. None establishes zero, success or completeness. Numeric
zero is a value when positively supported. Reconciliation chooses governing claims under explicit
policy; it does not choose a source solely because it was ingested later. Procurement's
[governing policy v1](../product/governing-claim-policy-v1.md) / ADR-023 defines predicate-specific
eligibility, effective intervals and explicit supersession. Models supply evidence; policy owns
the governing decision. The original and losing claims remain available in the ledger/archive.

The conceptual investigation chain is answer claim → calculation → operational state →
reconciliation → canonical identity → resolution decision → source assertion → mapped field →
structure → artifact. [Evidence and UX](evidence-and-ux.md) describes that drill-down; it is a
target chain, not proof that every historical record has every link. A caller must preserve
explicit missing-link and abstention states rather than fabricate provenance.

## Delivered runtime boundary and acceptance evidence

Contracts exist for all twelve logical stages. Actual package execution
is bounded: [#226](https://github.com/stauntonjr/procurement-intelligence-lab/issues/226) executes
INGEST through ASSERT; [#236](https://github.com/stauntonjr/procurement-intelligence-lab/issues/236)
adds explicit RESOLVE; [#239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239)
invokes only RECONCILE over selected validated retained RESOLVE producers. This does not establish
a fresh seven-stage multi-document run. Original local durable jobs remain five-stage under
[#232](https://github.com/stauntonjr/procurement-intelligence-lab/issues/232); the additive
[RESOLVE jobs profile](local-resolved-prefix-jobs.md) under #244 wraps six actual stages with
separate pins, identifiers and retention. Its Issue records exact main acceptance. Procurement has no
PREDICT, DECIDE or ACT executors/policies under this package contract; separate showcase paths do
not prove full-package execution. Broader Issue and milestone acceptance remains independent.

Existing executable ordering/type checks are
[the stage-registry contract tests](../../tests/contract/test_stage_contract_registry.py),
[universal semantic tests](../../tests/unit/test_universal_stage_semantics.py) and
[stage invariant regressions](../../tests/regression/test_stage_contract_invariants.py).
They validate the shared topology and typed distinctions, including a non-procurement fixture;
they do not benchmark identity quality, forecasting or production readiness. The Issue #20
delivery receipt records the documentation review, exact revision and verification commands.
