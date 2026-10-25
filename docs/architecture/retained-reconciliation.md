# Retained required-quantity reconciliation

Issue [#239](https://github.com/stauntonjr/procurement-intelligence-lab/issues/239),
[ADR047](../adr/047-retained-resolution-required-quantity-reconciliation.md) and the
[approved design](../superpowers/specs/2026-10-24-retained-resolve-reconciliation-design.md)
define this explicit local operation. The [qualification receipt](../development/evidence/issue-239/qualification.json) names tested
revisions. Exact protected delivery and main-pinned acceptance are recorded in Issue #239.

The caller selects one to eight already-retained [six-stage producers](planned-resolve-prefix.md)
and supplies synthetic authority attestations. Only RECONCILE executes now, once per admitted
call. Twelve current dispositions show its success and eleven NOT_EXECUTED entries. Historical
producer executions remain separate. Requested-operation completion can be true; package execution
completion is always false. There is no seven-stage prefix, durable reconciliation job or later
DERIVE through ACT execution.

## Inputs and decisions

Every producer must have the exact same four-part source scope and complete candidate semantic
snapshot, with the supported procurement_item/internal_sku normalized-exact resolution policy.
Duplicate execution, artifact, content hash or revision membership rejects. Repeated quantity rows,
unresolved identity, unknown/missing/negative quantities and unsupported units reject before
invocation. Each item/revision supplies one known nonnegative quantity in each units. Selected
supersession pairs must contain identical resolved item sets, including empty successors.
No quantity aggregation, deletion inference, conversion or source precedence is added.

The unchanged procurement-governing-claims/v1 policy selects approved, effective required-quantity
claims at the explicit as-of instant. Explicit supersession removes eligible predecessors. Equal
values from distinct-content revisions jointly govern and retain every source. Conflicting active
values or no active source produce UNRESOLVED decisions with domain audit dispositions and no
state. Zero and fractional quantities are valid. Newer capture time grants no authority.

Governed states contain only required_quantity/each, OBSERVED epistemic status, UNKNOWN freshness
and the ADR024 derived scope. Their separate domain audit records RECONCILED basis. Original
source scope remains visible; these states assert no procurement, outstanding, price or delivery
quantity and no human confirmation. Authority JSON is a trusted local synthetic attestation;
this operation does not verify enterprise approvals or signatures.

The strict authority JSON is exactly schema_version ("1.0") and producers (1–8 records).
Every record requires execution_digest, artifact_id, content_hash, revision_id,
supersedes_revision_ids, source_role, approval, effective_from, effective_until and document_at.
Approval is explicitly null or exactly record_ref/approved_at. effective_until is explicitly null
or later than effective_from. Timestamps are aware ISO8601; fixed offsets remain in identities.
The [approved wire table](../superpowers/plans/2026-10-24-retained-resolve-reconciliation.md#authority-and-policy-json)
pins all field lengths and values. Unknown/duplicate keys, missing required nullable fields,
nonfinite values and invalid Unicode reject. Producer ordering, metadata record ordering and JSON
whitespace do not change computation identity. Exact raw authority bytes and checksum remain
separate audit evidence, so receipt identity can differ.

## Run and retain

Install Python3.12 or3.13 with the storage extra. Set PIL_ASSERTION_ARCHIVE_DSN outside argv.
The earlier source, planned-prefix and resolved-prefix capabilities must already be initialized
and the selected producer results retained. Reconciliation needs storage even without --archive;
no command implicitly initializes a capability or imports producer results.

```sh
python -m procurement_intelligence_lab.interfaces.domain_package \
  --source-profile retained-resolved-required-quantity > operation-manifest.json
python -m procurement_intelligence_lab.interfaces.reconciliation_archive init
python -m procurement_intelligence_lab.interfaces.reconcile_resolved_package \
  --manifest operation-manifest.json --registry operation-registry.json \
  --config operation-config.toml --context operation-context.json \
  --governing-policy governing-policy.json --authority authority.json \
  --producer-digest "$PRODUCER_DIGEST" --as-of 2026-10-19T00:00:00Z --archive
```

Repeat --producer-digest for additional explicitly selected producers. Registry/config fixtures in
[tests/fixtures/retained-reconciliation](../../tests/fixtures/retained-reconciliation) are synthetic
repository examples, not implicit installed defaults. Pin your own code revision in context and
config application_version to the same 40-character lowercase Git revision. Context contains
exactly scope (tenant_id/project_id/site_id/version), run_id, code_revision and started_at. The
as-of and producer capture instants must not exceed started_at; as-of may precede ingestion.
The governing policy file pins profile, policy_id, predicate and quantity_unit exactly.

Limits: authority64KiB, context/policy32KiB each, manifest/registry/config1MiB each. Selected
producer graphs plus original source bytes have a combined4MiB and12,500 decoded graph-node
budget before invocation. Existing per-record codec bounds remain16MiB/50,000 nodes/depth64.
The result must fit the finite codec, including the complete retained export wrapper.

Optional --archive first checks readiness, then invokes, validates and atomically retains the
current result with immutable exact producer joins. Producers are never appended or recomputed.
Every retry invokes RECONCILE; same-computation retention preserves the first durable receipt.
Output separates recorded_producers, current_operation, archive_receipt and first_retained_operation.
Unknown commit acknowledgement means retention is uncertain; inspect history or retry the same
pins. It is not evidence of rollback.

## Source-free recovery

Recovery validates the recorded producer graphs, exact original source bytes and current policy
postconditions without original local input/config files or upstream executor construction.

```sh
python -m procurement_intelligence_lab.interfaces.reconciliation_archive show \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST"
python -m procurement_intelligence_lab.interfaces.reconciliation_archive history \
  --scope scope.json --limit 100 --after-sequence 0
python -m procurement_intelligence_lab.interfaces.reconciliation_archive content-manifest \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST"
python -m procurement_intelligence_lab.interfaces.reconciliation_archive export \
  --scope scope.json --execution-digest "$EXECUTION_DIGEST" --output retained.json
```

Scope files contain exactly the original four source-scope fields. History defaults100/max200;
nonnegative cursors allow sequence gaps. Export is atomic and never overwrites. It contains the
bounded result, authority evidence and recorded producer graphs, but not original source bytes.
The content manifest supplies exact recovery identities and commands. Export companion bytes
with resolved_execution_archive content and the selected producer digest. This evidence export
is not a self-contained source archive, an import or a new execution.

Failures are sanitized JSON stderr/exit2, with no success stdout, traceback or connection string.
Invalid metadata/admission, unsupported reconciliation input, unavailable storage/capability,
scoped not-found, immutable conflict, corrupt evidence and uncertain acknowledgement stay distinct.
Known producer recovery IDs accompany operation failures. A present result with missing joins,
corrupt producer/source bytes, rehashed invalid authority or invalid state fails integrity checks;
it never becomes empty success. SQL guards protect ordinary writes; database-owner bypass remains
outside this threat boundary. Bounded synthetic examples qualify integration, not general entity
resolution quality, enterprise approval correctness or broader M4 completion.
