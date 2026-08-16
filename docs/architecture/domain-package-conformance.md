# Domain-package conformance contract

Status: accepted architecture contract. This is the acceptance record for M0.33. It defines
what M0.34 must validate; it does not introduce a compiler, registry, planner, or new runtime
behavior on main.

Named verticals and their expansion status are tracked in the [domain vertical registry](domain-verticals.md).
The procurement mapping below is the current vertical's semantic baseline; the compiler contract
is intentionally reusable for a future package and does not imply that a second vertical exists.

## Scope and ownership

The four layers are normative:

| Layer | Owns | Excludes |
|---|---|---|
| platform stage catalog | stage order, input/output contracts, guarantees, neutral-mode meaning | procurement policy and deployment selection |
| domain package | stage modes, requirements, declarative policy/config/evaluation references, source-profile variants | ordinary provider/model/service/region names and executable callbacks |
| platform strategy/policy | reusable strategy meaning and parameter schemas | hidden provider behavior |
| runtime/deployment | implementation descriptors, capability advertisement, provider/model/service selection, credentials references | domain-name branching and semantic redefinition |

Domain authoring is side-effect-free declarative data. A package import must not perform I/O,
read ambient secrets, start a service, or supply arbitrary executor callbacks. A compiler and
runtime fail closed rather than infer missing bindings, capabilities, or semantics.

## Fixed catalog and neutral modes

Every DomainPackage supplies exactly one binding for every stage, in this fixed order:

INGEST -> STRUCTURE -> MAP -> NORMALIZE -> ASSERT -> RESOLVE -> RECONCILE -> DERIVE -> DETECT -> PREDICT -> DECIDE -> ACT.

EXECUTE invokes a selected implementation that satisfies the binding. PASSTHROUGH is valid only
when a source or prior stage already satisfies the output contract and a semantic trace records
that verification. EMPTY emits the named stage's typed empty result; it is a deliberate result,
never a synonym for unknown, failed, skipped, or omitted. These names describe logical semantics,
not a requirement that every stage be a separately scheduled process.

| Stage | Input -> output and guarantee | PASSTHROUGH prerequisite | EMPTY result |
|---|---|---|---|
| INGEST | source reference/event -> immutable artifact capture identity | a verified immutable artifact already exists | no captured artifacts |
| STRUCTURE | artifact -> StructuredDocument; physical/logical structure without domain meaning | input already satisfies StructuredDocument | no structured documents |
| MAP | structured document -> MappedDocument; schema meaning and source locations retained | mapped schema and source locations already satisfy the contract | no mapped documents |
| NORMALIZE | mapped values -> comparable observations with units, diagnostics, and provenance | values are already normalized and provenance-complete | no normalized observations |
| ASSERT | observations -> source assertions and entity mentions; claims remain distinct from truth | source assertions and mentions satisfy the assertion contract | no assertions or mentions |
| RESOLVE | assertions/mentions/context -> resolution decisions and canonicalized assertions; abstention remains valid | retained decisions satisfy the resolution contract | no resolution decisions because there are no mentions |
| RECONCILE | canonicalized assertions/policy -> reconciliation decisions and governed state; conflicts retained | governed state and its governing/losing-claim evidence satisfy the contract | no governed-state records |
| DERIVE | governed state -> deterministic derived facts with evidence links | facts retain their derivation/evidence contract | no derived facts |
| DETECT | state/derived facts -> evidence-backed anomalies, distinct from predictions/actions | prior anomaly records meet the policy/evidence contract | no anomalies detected |
| PREDICT | scoped evidence/state -> predictions with uncertainty and execution provenance | predictions meet uncertainty and provenance requirements | no predictions |
| DECIDE | facts/anomalies/predictions/policy -> decision or recommendation with authority/evidence | decision has policy, authority, and evidence | no decisions or recommendations |
| ACT | approved decision -> authorized, idempotent, auditable action result | existing action result has approval/idempotency/audit evidence | no action attempted |

A source profile may choose a validated binding variant, such as STRUCTURE(EXECUTE) for a PDF
and STRUCTURE(PASSTHROUGH) for a verified ERP event. It cannot omit a stage, add an edge, or
change this order.

## Meta-schema and compatibility

The initial compiled artifact uses domain_package_schema_version 1.0. Every package carries that
schema version, a stable domain ID, an independent domain version, all twelve bindings, and its
source profiles. A binding may contain only mode, capability requirements, declarative
domain-config references, policy references, evaluation-suite reference, and the stage-specific
neutral semantic where applicable.

- A stage-catalog/topology change, changed binding meaning, or required-field change is a major
  schema change and requires an ADR plus migration/conformance evidence.
- Backward-compatible additions use a minor schema version. A compiler must reject a newer minor
  version it does not explicitly support; it must not silently discard a new semantic field.
- Domain version changes are independent of schema versions. They identify changes to domain
  requirements, policy references, or configuration references.
- A source-profile variant has the same complete stage set as the base package and must validate
  against the same catalog version.
- The compiled manifest includes the schema version, domain ID/version, selected source profile,
  bindings, references, requirements, and neutral semantics. It excludes ordinary provider,
  model, service, region, credential, and deployment-package names.

The compiler's canonical JSON and manifest hash are M0.34 deliverables. This decision fixes their
semantic inputs, not their byte-level encoding implementation.

## Current procurement mapping

This mapping preserves what exists today and identifies deliberate gaps; it is not a claim that
the present BOM pipeline is already a DomainPackage.

| Stage | Current authoritative behavior | Ratified package implication |
|---|---|---|
| INGEST | read_bom_with_provenance captures XLSX bytes and appends an artifact hash to ProvenanceContext; the platform now defines `SourceReference` and immutable `Artifact`. | A future binding must populate the shared capture contract without changing public BOM behavior. |
| STRUCTURE / MAP | `StructuredDocument` and `MappedDocument` contracts are distinct, while XlsxStructuredBom still performs both stages in one adapter boundary. | Physical fusion remains valid only when both semantic records and their evidence can be traced. |
| NORMALIZE | `NormalizedObservation` now defines value/unit/diagnostic/epistemic semantics; current BomLine, BoqLine, and PurchaseOrderLine remain direct vertical records. | M1-M4 extraction must populate the shared observation contract without treating missing as zero. |
| ASSERT | SourceAssertion and assertions_for_bom retain source claim, evidence, and transformation event. | Binding must preserve claims before truth/canonical state. |
| RESOLVE | ResolutionDecision and resolve_identifier preserve resolved and unresolved outcomes with decision provenance. | Unresolved identity remains a valid output, not an empty result. |
| RECONCILE | project_operational_lines, the platform SourcePrecedencePolicy contract, and procurement reconcile_lines retain governing and losing evidence. | Binding selects declarative policy references; it does not select a reconciler provider. |
| DERIVE | `DerivedFact` plus existing EvidenceBackedResult/evidence chains define deterministic evidence-linked output. | Procurement application services have not yet adopted the explicit record everywhere. |
| DETECT | The platform Anomaly envelope and procurement typed details/detectors consume scoped expected/observed state and per-kind policies. | Binding carries requirements/policy references; detection does not decide or act. |
| PREDICT / DECIDE / ACT | Shared `Prediction`, `Decision`, `ApprovedDecision`, and `ActionResult` contracts enforce uncertainty, scope, authority, approval, idempotency, and audit invariants. No procurement executor is present. | Initial procurement bindings remain typed EMPTY; concrete policy/model/action work requires separate issues and evaluation. |

The semantic contract registry validates every catalog input/output name before compilation without
adding Python type names to the language-neutral manifest. C010 rejects a known-bad missing
registration.

## M0.34 conformance matrix

| Case | Required compiler outcome | Evidence layer |
|---|---|---|
| Missing stage binding | reject with stage-specific diagnostic | unit and contract |
| Duplicate stage binding | reject; exactly one binding per catalog stage | unit and contract |
| Unknown stage or reordered topology | reject; domains cannot define edges | contract and regression |
| Invalid mode / missing neutral semantic | reject; mode and typed output semantics must agree | unit and contract |
| PASSTHROUGH without output-contract verification requirement | reject | contract |
| EMPTY used for unresolved input or failure | reject; use typed unresolved/failure behavior instead | regression |
| Provider/model/service/region or executable callback in a binding | reject | unit and static policy |
| Unknown capability or incompatible source-profile variant | reject with typed capability/profile diagnostic | contract |
| Different source profiles with identical logical semantics | compile distinct selected-profile metadata without topology drift | contract and regression |
| Equivalent authoring data | emit byte-identical canonical JSON and manifest hash | regression |
| Newer unsupported schema minor or incompatible major | reject without silently dropping fields | unit and contract |
| Existing procurement semantics | no behavioral/provenance regression in assertions, resolution, reconciliation, state, and anomaly tests | regression and challenge |

M0.34 must attach each case to an executable test, fixture, or challenge result before it is closed.
