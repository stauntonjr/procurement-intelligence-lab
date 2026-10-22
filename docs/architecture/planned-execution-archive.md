# Completed planned-prefix archive

ADR-044 and Issues #228/#229 define opt-in retention of the actual planned
INGEST → STRUCTURE → MAP → NORMALIZE → ASSERT execution. The full physical plan,
resolved policy/config content identities, typed outputs, five events and twelve
stage dispositions are retained beside original source snapshots and bytes. The
seven later stages remain NOT_EXECUTED; this is prefix completion only.

Initialize a supported source archive, then its additive capability explicitly:

```sh
export PIL_ASSERTION_ARCHIVE_DSN='...'
python -m procurement_intelligence_lab.interfaces.assertion_archive init
python -m procurement_intelligence_lab.interfaces.planned_execution_archive init
python -m procurement_intelligence_lab.interfaces.execute_package source.xlsx \
  --manifest manifest.json --registry registry.json --config config.toml \
  --context context.json --normalization-policy policy.json --stop-after ASSERT --archive
```

The storage extra is required. Runtime admission precedes lazy storage construction;
storage readiness precedes source I/O. Every invocation executes all five stages.
Default execution without `--archive` keeps its original ephemeral JSON contract.
The neutral runner does not own storage or procurement policy.

One PostgreSQL transaction writes source content, snapshot, claim membership and the
new execution binding. Exact scope plus execution digest identifies a computation.
Retry admission compares full canonical computation, snapshot/policy parameters and
exact captured bytes. Only server completion time may differ. The first committed
full receipt and sequence remain retained. `execution_receipt` describes the current
invocation; `retained_execution_receipt` describes that first retained completion.
`archive_receipt` binds the execution and nested source receipt. No latest-winner
or governing-claim selection is implied.

Recover without the source, executors, manifest, registry or current config:

```sh
python -m procurement_intelligence_lab.interfaces.planned_execution_archive show \
  --scope scope.json --execution-digest SHA256
python -m procurement_intelligence_lab.interfaces.planned_execution_archive history \
  --scope scope.json --limit 100 --after-sequence 0
python -m procurement_intelligence_lab.interfaces.planned_execution_archive content \
  --scope scope.json --execution-digest SHA256 --output retained.xlsx
```

Scope JSON contains exactly tenant_id, project_id, site_id and version. History uses
an exclusive nonnegative sequence cursor, default limit100, maximum200. `has_more`
requires an actual extra matching row; only then does `next_after_sequence` name the
last returned sequence. No total count is inferred. Sequence gaps are valid. Export
is atomic and refuses to overwrite. All reader paths verify stored policy/domain
and source integrity; old assertion-archive readers still admit the source snapshot.

Failures use sanitized execution/archive codes, JSON stderr and exit2 without success
stdout. Missing or foreign-scope records are not-found; corruption is integrity failure.
Initialization is never implicit. A lost commit acknowledgement may follow a successful
commit: failure does not prove rollback. Use scoped recovery to inspect retention.

The allowlisted graph adds lowercase even-length `bytes-hex` for exact physical-plan
bytes, preserving old snapshot wire bytes and16MiB/50,000-node/depth64 bounds. Ordinary
SQL mutations are guarded; database-owner bypass is outside this trusted local boundary.
There is no attempt journal, result cache, lookup-before-execution shortcut, queue,
automatic retry/recompute, request exactly-once guarantee, later-stage execution,
production authentication, backup/HA or deployment qualification.
