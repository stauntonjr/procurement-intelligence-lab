# ADR-038: Atomically archive complete assertion snapshots and source bytes

Status: accepted for the owner-authorized durable archive increment under #37/#13.

Postgres remains canonical (ADR-001). Add a neutral frozen DocumentSnapshot and ArchiveReceipt,
and a batch AssertionArchive port, without changing the legacy single-assertion AssertionLedger
contract. The snapshot retains structure/mapping/observations/claims/mentions, all five events,
normalization policy reference and assertion origin. No resolution, authority/effectivity choice,
correction policy or additional logical stage is introduced. #37/#41 retain correction semantics.

A snapshot and its exact captured bytes commit in one transaction. Stable snapshot identity and
canonical payload identity are distinct: identical retry returns the original receipt, while
same identity/different payload fails. Conflicting revisions remain independent. Unique claim
identity and membership prevent silent duplicate claims. Global sequences are monotonic, not
necessarily contiguous; no exactly-once queue-processing claim is made under #36.

Use a versioned, content-addressed typed JSON DAG with fixed class/enum registrations supplied
by bootstrap. Values retain Decimal representation, dates, aware fixed-offset datetimes and
concrete enum types. Shared nodes are deduplicated by content, independent of Python object
sharing. No pickle or dynamic imports. Strict schema/field/type/hash/reachability/size checks and
reconstructed semantic validation reject corrupt or unsupported data. A checksum detects
inconsistency, not a malicious database owner who replaces all coordinated records.

The Postgres adapter owns schema, transactions and driver failures. Schema initialization is an
explicit local administration command; reads/appends do not silently create or migrate tables.
Append-only SQL guards reject ordinary update/delete, while exact replay uses conflict checks
without updating prior data. Content-addressed bytes may be shared physically; every public read
still requires exact tenant/project/site/version scope. Missing data fails explicitly. Scoped
history lists materialization receipts in sequence order; it does not select governing state.

The existing BOM CLI opts into persistence with --archive after --assertions and explicit policy.
Bootstrap injects process-local captured-content retention into the same five-stage service, then
materializes from those bytes rather than reopening a source URI. A separate archive CLI supports
init, scoped show/history and source export to an explicit non-overwriting path after restart.
Reads reconstruct the prior result without reprocessing the original source. DSNs come from a
named environment variable and never enter provenance, payloads or public errors.

The driver is an optional storage extra; default package commands remain usable without it.
A dedicated ephemeral Postgres instance qualifies transactions, concurrency, corruption handling,
restart/public CLI and clean-wheel behavior locally and in required CI. Existing shared databases
are never used for tests. This is bounded local storage qualification, not production deployment,
backup/HA, distributed ingestion, user authentication or completion of #13/#35/#36/#37.

Transaction and locking mechanics follow the upstream
[Psycopg transaction contract](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) and
[Postgres 16 explicit-lock semantics](https://www.postgresql.org/docs/16/explicit-locking.html).
