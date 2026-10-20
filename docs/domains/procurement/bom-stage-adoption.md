# BOM capture, structure and mapping adoption

The default remains these three stages. Issue #209 adds an explicit opt-in
[BOM normalization path](bom-normalization.md) with declared units/currency and a fourth event.
Statements below about normalization remaining separate describe this three-stage boundary.

Issue [#207](https://github.com/stauntonjr/procurement-intelligence-lab/issues/207), M1, parent #7,
implements the first three shared strategy contracts from ADR-022. The real path is
`SourceReference -> Artifact -> StructuredDocument -> MappedDocument`. These are actual synchronous
stage outputs, not planning fixtures. The existing BOM/demo services retain their legacy path;
no full DomainPackage executor or later-stage execution is inferred.

## Ownership and execution

`ports/artifacts.py` defines `ArtifactContentStore`. `LocalFileIngest` reads an explicit local
file URI once and stores immutable bytes by SHA-256. `MemoryArtifactContent` is process-local;
retaining bytes across source mutation/deletion proves only in-process snapshot retention, not
durable storage, crash recovery, multi-tenant authorization, replay/idempotency or a queue.

`XlsxStructure` reads by captured hash through the port, verifying hash and byte length before
parsing. It never reopens the source URI. Shared `xlsx_cells.py` mechanics retain the existing
legacy decoder behavior and C002's sparse-coordinate oracle. The new structurer admits unique
positive row/cell coordinates, resolves internal worksheet targets against `/xl/workbook.xml`
(including package-absolute and relative dot-segment paths, following the
[OPC source-part rule](https://learn.microsoft.com/en-us/dotnet/api/system.io.packaging.packagerelationship.targeturi?view=netframework-4.8.1)), resolves shared/inline strings, and emits generic `row`/`cell`
elements with physical worksheet coordinates. It assigns no schema meaning or business units.
Row/cell ordering follows source coordinates; blank rows without cells emit no elements.

The adapter rejects inconsistent/duplicate row/cell coordinates, duplicate archive members,
ambiguous worksheet/relationship identifiers, external worksheet relationships, literal target URI
whitespace/control characters and empty path segments (before URL normalization), unknown cell types,
conflicting scalar/inline/shared-string representations, missing/non-worksheet relationship types, wrong XML part roots or nested/duplicate sheetData,
invalid shared-string indices, formulas
and merged cells, unsupported media types and malformed
archives/XML. Admitted cell types are `n`, `s`, `inlineStr`, `str`, `b` and `d`; values remain raw
text without interpreting numbers, booleans or dates. String decoding accepts plain text and
validated rich display-text runs, ignoring XML indentation; phonetic annotations and malformed
nested text are unsupported. Error cells (`e`) are unsupported. Formula caches are not recalculated or accepted as verified values. Coordinates
must fit the [documented XLSX grid](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits):
1,048,576 rows and 16,384 columns. Bounds are checked before dense-row mechanics allocate padding.
This is a constrained table adapter, not general Excel rendering, formula evaluation or OCR.

`domains/procurement/mapping.py` owns `BomTableMap`. It validates the first source row's four
ordered, distinct BOM headers from `BOM_TABLE_SCHEMA`. It maps A–D to `sku`, `description`,
`quantity`, `unit_price`, retaining raw strings and exact cell evidence. Additional cells remain
explicit `unmapped.<column>` fields with diagnostics, including when trailing labels repeat a
required label or one another. Only A–D govern header matching; extras never silently acquire
business meaning.
Multiple rows with the same SKU remain distinct. A row with a missing SKU is retained.

Empty/blank field values, including whitespace-only text, are unresolved with diagnostics, not zero.
The structured cell retains its exact text; nonblank mapped strings retain surrounding whitespace.
A physically missing column
retains the source row evidence and reports `missing column X`; an explicitly blank cell retains
its own cell evidence and reports `blank cell`. Missing-column evidence identifies the actual
populated source row, not an invented source cell. Raw `0`, `-1`, `0.5` or `not-a-number` remains
observed text. Normalization, quantities/units/currency and invalid-number policy belong to #31;
assertions, resolution, authority and broader #32/#33 work are not implemented here. A header-only
workbook maps to zero fields; a workbook without the required headers fails mapping.

`application/document_stages.py` orchestrates exactly one capture through the three Protocols,
rejecting empty/multiple captures, foreign artifact/document lineage or ignored injected component
provenance. It creates distinct transformation events only after successful stages. Capture uses
the source-reference ID; structure uses the artifact ID and capture parent event; mapping uses the
structured-document ID, schema reference and structure parent event. Output records and events
retain their component versions, scope and explicit observation/capture context. Each stage appends
its direct input to caller-injected snapshot IDs with stable deduplication, preserving upstream
execution inputs. `bootstrap.py`
wires the local content store, generic structurer and procurement mapper. Platform and ports have
no vertical imports. Provider callbacks are absent from the DomainPackage.

## Public caller

```bash
python -m procurement_intelligence_lab.interfaces.bom_stages \
  /path/to/source.xlsx --context /path/to/context.json
```

An explicit context file has this shape:

```json
{
  "scope": {"tenant_id": "synthetic", "project_id": "example", "site_id": "lab", "version": "1"},
  "observed_at": "2026-10-19T00:00:00+00:00",
  "captured_at": "2026-10-19T00:00:01+00:00",
  "source_version": "source-revision-1",
  "run_id": "inspection-1",
  "code_revision": "caller-supplied-code-revision"
}
```

`source_version` may be absent/null; all other fields are required and unknown/duplicate keys fail.
Scope identifiers, run/code identities and timestamps must be non-empty strings; timestamps must
be timezone-aware and capture cannot precede observation. Scope is supplied metadata, not a grant
of access. The local CLI runs with the user's OS file access and makes no production authentication
or isolation claim. Caller-supplied code identity is retained as declared metadata, not a build
attestation. The context hash is retained as configuration identity; dependency-lock identity is
explicitly unavailable, and execution is labeled `local-uncontainerized`.

Success prints deterministic JSON containing the source/artifact, generic structure, raw mapped
fields and all three transformation events. Fixed explicit context/source bytes produce stable
IDs and payloads. Changes to source reference/scope, bytes, capture time or provenance remain
distinguishable. Later stages do not appear as executed or empty successes. Failure exits 2,
emits no partial-success JSON, and returns `code/category/message` on stderr:

| Failure | Code/category |
|---|---|
| Unsupported local URI | `pil.input.source_reference_unsupported` / input |
| Unreadable source | `pil.infrastructure.artifact_source_unavailable` / infrastructure |
| Missing/corrupt captured bytes | `pil.infrastructure.artifact_content_invalid` / infrastructure |
| Unsupported/malformed worksheet | `pil.interpretation.document_structure_invalid` / interpretation |
| Invalid/ambiguous BOM mapping | `pil.interpretation.schema_mapping_invalid` / interpretation |
| Invalid context or returned stage lineage | `pil.input.document_stage_invalid` / input |
| Capture before observation | `pil.input.temporal_contract_violation` / input |

## Acceptance and limits

Contract tests pin sparse/reordered cells, source mutation/deletion, missing/tampered content,
empty/header-only documents, duplicate coordinates/headers/SKUs, missing/unmapped fields, formula
and merge rejection, numeric text, scope identity, timestamps and XLSX boundaries. Subprocess CLI
tests inspect actual outputs, raw values, evidence and transformation parents. Clean-wheel smoke
runs the installed command outside the checkout in two environments against the same explicit
source/context and compares identical output; unsupported-source failures remain typed.

The [conformance manifest](../../../evals/extraction/bom-stages-v1/manifest.json) pins the existing
metadata-complete `synthetic_bom_stages.xlsx` sample and eight BOM revisions from the admitted four-project corpus, excluding PO,
quote and commitment roles. Its independent source-XML expectations check row grouping, physical
cell text/coordinates, raw mapped fields and the actual attached field evidence separately;
evidence artifact/hash identity must match the captured source. Extra `Line ID` cells are deliberately
unmapped. The historical `synthetic_bom.xlsx` remains byte-identical for existing demo/reproduction
evidence; it lacks a worksheet relationship type and is rejected by the new strict caller. The new
sample preserves its table values while adding that explicit relationship metadata, with a separate
file identity/hash. Workbook, relationship, worksheet and shared-string part roots are validated
before extraction. Shared strings come from one explicit internal workbook relationship; an orphan
canonical table is rejected rather than guessed. Root package relationships are optional in this
fixed-path profile, but when present must uniquely identify internal `xl/workbook.xml`; contradictory
or arbitrary workbook layouts fail closed. This is a constrained table profile, not full OOXML
schema validation.
The initial gold construction omitted those extras; correcting the source-derived
expectation preserved the specified unmapped-field behavior rather than dropping source data.
Nine workbooks yield 1,608 mapped fields. The runner records input and layer hashes, record counts,
per-source latency, verified checkout revision and manifest hash; inference calls/cost are zero and compute cost
is unavailable. Expected digests are conformance checks, not an OCR quality score or #30's external
parser comparison. The runner derives HEAD and requires a clean tracked/untracked worktree, verifies
that imported stage code belongs to that checkout, and rechecks the context before emitting a report.
An optional `--revision` is an exact HEAD assertion; mismatched, dirty or foreign-code contexts exit 2
without writing a report. Evaluator files are not shipped as runtime resources.

```bash
python tools/benchmark_bom_stages.py --revision CODE_REVISION --output /tmp/bom-stage-conformance.json
```

The general planner remains planning-only. Real NORMALIZE/ASSERT adaptation is next and must
resolve the later Issues' semantics before extending this caller. Durable content/ledger storage,
replay, runtime provider construction, full extraction and production deployment remain separate.
