# Explicit planned RESOLVE prefix

Issue [#236](https://github.com/stauntonjr/procurement-intelligence-lab/issues/236),
[ADR046](../adr/046-explicit-planned-resolve-prefix.md) and the
[approved design](../superpowers/specs/2026-10-24-planned-resolve-prefix-design.md)
define this opt-in profile. It invokes INGEST, STRUCTURE, MAP, NORMALIZE, ASSERT and
RESOLVE once per execution. All twelve stage dispositions remain visible; the last six
are NOT_EXECUTED and package completion is false. The original ASSERT-only execution,
archives and local processing jobs retain their contracts. Local jobs do not accept RESOLVE.

The caller supplies a bounded local catalog in the declared `procurement_item` /
`internal_sku` namespace. This is explicit identifier matching, not an authoritative
inventory, supplier registry or real-world identity proof. No candidates are inferred from
source rows. The deterministic `bom-normalized-exact@1` policy reuses casefold/alphanumeric
normalization: one matching key resolves, no match or multiple normalized keys abstains.
Punctuation-only mentions abstain. Null/blank SKU rows have no mention and remain unlinked.
All original claims and numeric values remain intact. Only resolved rows gain canonical links.
Every decision retains its exact HAS_SKU claim, row, policy, full matching keys and sixth event.

## Execute

Install the wheel with Python3.12 or3.13; base execution has no third-party runtime dependency.
The example files below are explicit synthetic deployment/test inputs in the repository,
not packaged defaults. Copy and pin their scope, timestamps, code revision and application
version for your execution. The selected registry advertises six actual implementations;
its later fixture entries describe planning compatibility only.

```sh
python -m procurement_intelligence_lab.interfaces.domain_package > manifest.json
python -m procurement_intelligence_lab.interfaces.execute_resolved_package source.xlsx \
  --manifest manifest.json \
  --registry tests/fixtures/resolved-execution/procurement-registry.json \
  --config tests/fixtures/resolved-execution/procurement-config.toml \
  --context tests/fixtures/bom-stages/context.json \
  --normalization-policy tests/fixtures/bom-stages/normalization-policy.json \
  --resolution-policy tests/fixtures/resolved-execution/resolution-policy.json \
  --candidate-snapshot tests/fixtures/resolved-execution/candidate-snapshot.json \
  --stop-after RESOLVE
```

The context `code_revision` must equal config `application_version` (the synthetic config
uses `test-revision`). The catalog schema is the exact JSON object in
[candidate-snapshot.json](../../tests/fixtures/resolved-execution/candidate-snapshot.json):
schema_version1.0, catalog_id, catalog_revision, four-field scope, entity_type,
identifier_namespace, effective_at and keys. Bound:32KiB UTF-8,0–256 unique raw keys,
1–256 Unicode characters/key, nonblank. Exact duplicate keys reject; normalized collisions
are retained and force abstention. Unknown/duplicate JSON fields, unsupported policy,
wrong scope/version/namespace and future timestamps reject before capture or storage.
Catalog effective time and source observed time cannot exceed pinned capture/start time;
o extra freshness rule is invented. Original timezone offsets are retained.

Canonical sorted keys determine semantic identity. Whitespace/JSON formatting and input
key order do not change computation identity. Raw catalog bytes and SHA256 remain audit
evidence and can change receipt identity. The output separates `execution_receipt` (six)
and `prefix_execution_receipt` (five), outcomes, original claims, canonical links and
unlinked claim IDs. No cache, run journal or later authority stage is updated.

## Explicit retention and source-free recovery

Install the `storage` extra and set `PIL_ASSERTION_ARCHIVE_DSN` outside command arguments.
Initialization of each capability is deliberate; the resolved capability requires both
predecessors already initialized. No runtime command silently creates schema.

```sh
python -m procurement_intelligence_lab.interfaces.assertion_archive init
python -m procurement_intelligence_lab.interfaces.planned_execution_archive init
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive init
# Add --archive to the execution above, then retain its execution_digest.
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive show \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST"
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive history \
  --scope scope.json --limit 100 --after-sequence 0
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive content \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST" --output recovered.xlsx
python -m procurement_intelligence_lab.interfaces.resolved_execution_archive export \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST" --output retained.json
```

`scope.json` contains exactly tenant_id/project_id/site_id/version. History limit1–200
and nonnegative sequence cursors are scope-local; sequence gaps are allowed. Exports write
atomically and never overwrite. `content` recovers exact source bytes; `export` emits the
bounded allowlist graph with original catalog bytes, recorded policies, full six-stage
receipt and separately retained first-five result. It is evidence export, not an import
or execution command. Inspection needs no original source/catalog/config file, current
executor construction or network beyond the chosen storage connection.

Source, five-stage result and six-stage result are retained in one transaction. Exact retries
keep the first durable record, while every new execution actually invokes all six stages.
`retained_execution_receipt` is the first six-stage receipt;
`retained_embedded_prefix_execution_receipt` is its embedded five-stage receipt;
`retained_prefix_execution_receipt` may be an earlier separately retained five-stage receipt.
Recovery displays retained evidence without claiming a new invocation. Unknown acknowledgment
means retention is uncertain: retry with the same pins or inspect history, never infer rollback.

Failures use sanitized JSON stderr/exit2: invalid input/admission, unavailable capability,
not-found within exact scope, immutable conflict or corrupt retained evidence. A present record
with missing linked source/prefix, checksum failure or unsupported recorded domain semantics
fails integrity validation; it cannot become success, empty or not-found. SQL guards protect
ordinary writes; the database owner can bypass guards and is outside that threat boundary.

The synthetic rule corpus qualifies integration and retained evidence only. It is development
material, not held-out entity-resolution quality evidence or completion of broad Issue#14/#45.
