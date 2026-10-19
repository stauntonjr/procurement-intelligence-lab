# Procurement DomainPackage v0.1.0

Issue #201 supplies the first real declaration under ADR-022. The package lives in
`domains/procurement/package.py`, uses DomainPackage schema `1.0`, and exposes the
`bom-table` source profile at version `1.0.0`. It describes the existing constrained
BOM semantics; it is not a runtime implementation registry or an executable plan.

## Public command

```bash
python -m procurement_intelligence_lab.interfaces.domain_package
python -m procurement_intelligence_lab.interfaces.domain_package --source-profile bom-table
```

Both commands print the compiler's canonical JSON followed by one newline. They
perform no source ingestion or model call. The composition root selects the shipped
procurement declaration, then calls the same domain-neutral compiler used by the
conformance suite. Python callers may use `bootstrap.compile_procurement_manifest()`
to obtain canonical bytes and their SHA-256 manifest hash. The trailing CLI newline
is not part of that hash. Unknown or empty profile names return exit 2, emit no
manifest, and write JSON compiler diagnostics to stderr with code
`pil.input.domain_package_invalid`, category `input`, and specific issue codes such as `unknown_source_profile`.
Selection is exact; case or whitespace is not silently corrected.

## Domain-owned source schema

`domains/procurement/source_schema.py` owns the immutable `BOM_TABLE_SCHEMA`:

- config reference `procurement.mapping/bom-table@1`;
- existing provenance schema identity `bom-xlsx-v1`;
- default worksheet `BOM`;
- ordered first columns `SKU`, `Description`, `Quantity`, `Unit Price`.

The XLSX adapter consumes this schema while retaining its own file/XML mechanics,
implementation name/version and transformation-event construction. Trailing source
columns remain permitted. Missing/reordered/duplicate required headers retain the
existing adapter failure. The original source rows, sparse column coordinates,
artifact hashes and transformation links remain authoritative. Quantities still
use the existing Decimal parsing behavior; absent prices remain absent. This slice
does not introduce currencies, broader unit normalization or new numeric policy.

## Stage and reference catalog

These versioned reference meanings name the current behavior. They are not provider
registrations, callbacks or proof that universal strategy executors are available.
The compiler currently validates reference syntax; a runtime's reference-resolution
and capability-admission rules are subsequent work. Each reference's evaluation
suite is the listed repository test surface at version 1, not a claim that every
broader milestone criterion is complete.

| Stage | Mode and requirements | Config/policy meaning | Evaluation reference and current evidence |
|---|---|---|---|
| INGEST | EXECUTE | Capture source bytes/hash and retain capture identity | `procurement.ingest/bom-capture@1`; `tests/unit/test_xlsx_adapter.py` |
| STRUCTURE | EXECUTE; `tables` | Retain physical worksheet/row/cell locations; physical fusion with mapping remains possible | `procurement.structure/bom-locations@1`; `tests/contract/test_xlsx_coordinates.py` |
| MAP | EXECUTE | `procurement.mapping/bom-table@1`: the domain-owned schema above | `procurement.mapping/bom-table@1`; `tests/contract/test_procurement_package.py`, `tests/unit/test_xlsx_adapter.py` |
| NORMALIZE | EXECUTE | `procurement.normalize/bom-decimal@1`: existing Decimal quantity/optional-price parsing, preserving missing price | `procurement.normalize/bom-values@1`; `tests/unit/test_xlsx_adapter.py`, `tests/unit/test_bom.py` |
| ASSERT | EXECUTE | `procurement.assert/bom-claims@1`: SKU, description, quantity and available price claims before resolution, with source/transformation links | `procurement.assert/bom-evidence@1`; `tests/unit/test_xlsx_adapter.py`, `tests/unit/test_pipeline.py` |
| RESOLVE | EXECUTE; `authoritative_ids`, `abstention` | `procurement.resolve/normalized-exact@1`: exactly one normalized identifier match resolves; zero or multiple matches remain unresolved | `procurement.resolve/bom-identifiers@1`; `tests/unit/test_pipeline.py`, `tests/unit/test_resolution.py` |
| RECONCILE | EXECUTE | `procurement.reconcile/explicit-source-precedence@1`: explicit source precedence, conflict/losing-claim retention; no inference from collection order | `procurement.reconcile/bom-conflicts@1`; `tests/unit/test_reconciliation.py`, `tests/unit/test_pipeline.py` |
| DERIVE | EXECUTE | `procurement.derive/bom-queries@1`: deterministic existing SKU/GPU/cost queries with evidence and absent-price abstention | `procurement.derive/bom-queries@1`; `tests/unit/test_bom.py` |
| DETECT | EXECUTE; `abstention` | `procurement.detect/qualified-assessment@1`: typed per-kind policies and qualified expected/observed assessments under ADR-026; additional assessment inputs are required | `procurement.detect/qualified-assessment@1`; `tests/contract/test_anomaly_assessment.py` |
| PREDICT | EMPTY | `no_predictions`; no procurement forecast executor | No execution/quality claim; #61 owns future forecasting |
| DECIDE | EMPTY | `no_decisions_or_recommendations`; no procurement decision-policy executor | No execution/authority claim; #65 owns future decision support |
| ACT | EMPTY | `no_action_attempted`; no procurement action executor | No external action or approval authority is granted |

The package always retains every logical stage in platform order. Unresolved
resolution, a missing observed quantity or failed assessment must never be
represented by an EMPTY binding. EMPTY here describes only intentionally absent
late-stage capabilities. Existing human review and saving a review brief do not
become procurement DECIDE/ACT executors merely because those workflows exist.

## Delivery boundary and continuation

The installed command and schema extraction are the first package adoption slice.
The existing application still invokes procurement services directly. Shared
StructuredDocument/MappedDocument/NormalizedObservation/OperationalState adaptation,
registry descriptors, runtime capability validation, physical planning, policy
parameter loading and semantic execution traces remain subsequent implementation.
BoQ/PO source profiles and complete procurement-package extraction remain open;
neither source format is silently treated as a BOM. The package may specify an
EXECUTE requirement even when the future runtime has no compatible implementation;
that future runtime must fail closed, rather than fabricate an EMPTY success.

No platform/port dependency points into procurement, and no domain-name selection
is added to the compiler. A source-schema, policy or requirement change must review
its independent package/profile version and retain deterministic conformance and
business/provenance regression evidence.
