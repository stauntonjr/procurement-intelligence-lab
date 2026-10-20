# Durable source assertion archive

Issue #213 is the first durable materialization under #13/#37, following #211. Postgres is canonical
(ADR-001); [ADR-038](../adr/038-atomic-postgres-assertion-archive.md) records this bounded contract.
This trusted local developer interface is separate from the demo and general physical planner.

Install the optional driver and explicitly initialize a dedicated database:

```bash
uv sync --extra storage
# Set PIL_ASSERTION_ARCHIVE_DSN privately for the selected database.
uv run --extra storage python -m procurement_intelligence_lab.interfaces.assertion_archive init
uv run --extra storage python -m procurement_intelligence_lab.interfaces.bom_stages \
  src/procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx \
  --context tests/fixtures/bom-stages/context.json \
  --normalization-policy tests/fixtures/bom-stages/normalization-policy.json --assertions --archive
```

`--archive` requires assertions and explicit normalization policy. Without it, existing three/four/
five-stage outputs and identifiers remain compatible. Capture uses the same injected staging
content store, then submits its exact captured bytes and immutable snapshot to the archive port.
It never reopens the original URI to persist data. The archive receipt is materialization evidence,
not a sixth logical stage. Policy declarations are retained with their reference, without inference
from observed units or currencies. The reader revalidates BOM policy and assertion postconditions.

One transaction retains bytes, the full structured/mapped/normalized/asserted snapshot, all five
transformations, and unique claim identities/membership. Identical snapshot retry returns its
original receipt without new rows. Reusing an immutable identity with different canonical payload
fails. A changed source, scope, execution/configuration or declared code revision can identify a
new processing result; deduplication is scoped to exact immutable identities. This does not claim
queue/job exactly-once processing under #36. Conflicting rows and revisions are never overwritten.
Receipts have global monotonic sequences, with possible rollback gaps, and retain the explicitly
injected assertion recording time separately from source observation and capture times.

Each snapshot uses a versioned, content-addressed typed JSON graph. Explicitly registered frozen
records and concrete enums retain typed Decimal/date/datetime values and tuple structure. Equal
record content deduplicates regardless of Python object sharing. The portable timestamp profile
admits timezone-aware fixed-offset datetime values; other timezone classes fail explicitly. The
wire limit is 16 MiB, 50,000 record nodes and depth 64. Unknown schema/types/fields, duplicate keys,
wrong hashes, orphan records, invalid semantic objects and unsupported scalars fail closed. The
codec never imports a class named by stored data and never uses pickle. Bootstrap registers
procurement enums; neither the port nor shared semantics imports procurement.

Create a scope JSON containing exactly `tenant_id`, `project_id`, `site_id`, and `version`, using
the scope in the archive receipt. Then read in a fresh process even after the original file moves:

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.assertion_archive \
  show --scope scope.json --snapshot-id document-snapshot-v1:RETAINED_ID
uv run --extra storage python -m procurement_intelligence_lab.interfaces.assertion_archive \
  history --scope scope.json
uv run --extra storage python -m procurement_intelligence_lab.interfaces.assertion_archive \
  content --scope scope.json --snapshot-id document-snapshot-v1:RETAINED_ID --output retained.xlsx
```

`show` reconstructs the prior evidence payload, provenance and policy without running the original
parser/normalizer. `history` returns immutable materialization receipts in sequence order, not a
governing source selection or effective-time query. An empty history is distinct from a missing
snapshot. Source export is verified against the captured hash/length and atomically linked to a
new output path; existing files are never overwritten. All reads, including content, require the
exact scope/version. Content blobs can be shared physically, but hashes are not a public unscoped
lookup API. The CLI does not establish multiuser authentication or operational-agent authority.

Initialization is explicit and supports schema version 1 only. Reads/appends do not create tables
or migrate schemas. Transactions serialize writers at the batch boundary, and SQL guards reject
ordinary UPDATE/DELETE/TRUNCATE. There is no update/delete API. Database owners can bypass guards;
checksums are integrity evidence, not a guarantee against coordinated malicious database edits.
No backup, restore, HA, retention or production deployment qualification is claimed.

Typed failures use `pil.input.archive_contract_invalid`, `pil.input.archive_not_found`,
`pil.policy.archive_conflict`, `pil.infrastructure.archive_integrity_invalid`, or
`pil.infrastructure.archive_unavailable`. They return exit 2, sanitized stderr JSON and no partial
success stdout. Driver errors, connection strings and credentials never enter public errors or
provenance. A base wheel without the optional driver returns a typed storage-extra diagnostic.
Argument syntax/help uses argparse. Existing normalization and stage failure codes remain intact.

Tests use an explicitly selected disposable Postgres instance via `PIL_TEST_POSTGRES_DSN`, with a
unique schema per test and cleanup limited to that schema. Required CI coverage/contract/integration/
package jobs run a pinned multi-platform Postgres 16 image. Local contract evidence covers atomic
rollback after a mid-write SQL failure, concurrent retry, restart, conflict retention, malformed
schema/content/claim membership, immutable guards, exact source metadata and scope isolation. Real
subprocess and installed-wheel tests prove capture → source deletion → show/export, with exact
bytes and no-overwrite errors. Without a test DSN, storage tests explicitly skip and package smoke
reports storage qualification not requested; that is not durable-storage acceptance evidence.

#13/#37 stay open for broader assertion/correction/supersession/review schemas and production storage
qualification. #35 owns general bounded EvidenceTrace traversal; #36 owns listener/job/attempt/queue
processing; #38/#41 govern temporal decisions and human correction policy. Issue #216 adds [document-value review lineage](document-review.md) as a separate append-only journal.
Other review workflows and controlled downstream recomputation remain subsequent work.
