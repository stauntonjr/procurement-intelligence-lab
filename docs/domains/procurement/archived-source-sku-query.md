# Executed source-SKU query and retained dependencies

Issue #220 (M2, parent #35), ADR-041, follows [declared dependency impact](../../architecture/correction-impact.md).
The first actual adopted producer computes distinct **observed source SKU strings** from one exact
archived BOM. It does not resolve canonical identity, select a governing revision, calculate current
requirements or adopt the universal DERIVE stage. Existing demo queries remain compatible.

The frozen domain SourceSkuQuery retains its exact DocumentSnapshot and fixed deterministic
component/policy `procurement-source-sku-set` / `source-sku-set/v1`. It shares the existing set/sort
helper with `distinct_skus`. Duplicate source rows remain distinct assertion inputs; only equal
source strings deduplicate in the result. Case variants stay distinct. Every SKU field is a data
input, including missing SKU claims. Descriptions, quantities and prices do not contribute data edges.

Complete inputs return an observed source set. Any missing/blank SKU returns `value: null` and
`status: unresolved`; `known_source_skus` is a separately labeled partial set, with exact missing
assertion IDs. It is never a complete subset or numeric zero. Header-only/no-SKU and more than32
SKU fields fail `pil.input.source_query_invalid`: the existing per-producer data-input bound is explicit.
Source assertions, original evidence and source versions remain unchanged.

The application executes the producer synchronously and builds its real TransformationEvent and
DependencyManifest; this caller never accepts a caller-authored graph or query output. Query IDs
bind source, result/status, policy and a full execution SHA256 including timestamps/parent metadata.
The event pins every consumed SKU claim and the upstream ASSERT event. Producer output must retain
the exact supplied source and execution metadata. Registration uses the existing port/schema1,
checks source membership and samples its server recording clock after computation. No old record
wire shape, archive1/review1/dependency1 schema, or logical stage changes.

Initialize archive and dependency storage explicitly. The private DSN remains
PIL_ASSERTION_ARCHIVE_DSN and the trusted registrar identity PIL_DOCUMENT_REVIEWER_ID. Application
execution requires REVIEW plus READ_EVIDENCE and matching request scope before database I/O. IDs,
principal, scope and execution metadata are validated before I/O. No operational-agent tool gains
authority; this shell configuration is not production authentication.

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.correction_impact init
uv run --extra storage python -m procurement_intelligence_lab.interfaces.archived_bom_query \
  --scope scope.json --snapshot-id '<exact archived snapshot_id>' \
  --request-id 'source-skus-run-1' --context query-context.json
```

The bounded32KiB UTF8 context has exactly these keys. Use an aware fixed-offset time at or after
source recording and no later than the server clock; the code revision is an operator-pinned local
manifest identity, not independently attested production provenance:

```json
{"run_id":"source-skus-run-1","code_revision":"<checkout or artifact revision>","started_at":"2026-10-21T12:00:00+00:00"}
```

Workflow/component/policy identities, exact source pin, local image identity and config digest are
composed at the boundary; raw environment and client recorder/recording-time overrides are not
accepted. Duplicate/deep/oversized/malformed JSON, bad Unicode/IDs/argument syntax and invalid
context time fail sanitized JSON/exit2 without partial-success stdout. Backend/archive/domain
failures preserve their existing typed envelopes; no raw DSN/driver errors are published.

Results contain the source value/diagnostics, input assertion IDs and field evidence, actual event
and provenance, plus immutable dependency receipt/digest. `producer_execution: synchronous_local_query`
means the function ran on this call. `execution_context_basis: caller_pinned_local_manifest` limits
the provenance claim. Query values are **not stored in a new result cache**: exact explicit retries
re-execute from the immutable archive and return the first dependency receipt/time. Changing a reused
request's source/context/actor conflicts; a new request can retain a separate execution. No exactly-once
execution, production attestation or complete consumer registry is claimed.

A subsequent approved document-value SKU correction can be inspected with the existing
`interfaces.correction_impact inspect` using this result's dependency_snapshot_id. Its affected
reference equals this executed query's reference_id. Approval does not apply the proposed SKU or
change the original query; explicit replay against the same source still returns the original set.
A non-SKU correction is not a registered root in this producer's manifest and fails typed not-found;
it is not a claim that all other consumers are unaffected. Coverage remains registered_graph_only,
global completeness not_evaluated, with no automatic invalidation/recomputation or governed-state change.

Acceptance includes domain/legacy compatibility, real isolated Postgres retry/conflict/restart,
actual subprocess and parser source-query -> SKU review -> impact, and a clean installed-wheel
archive capture/source deletion -> real producer -> registration -> human correction -> impact probe.
The old declared SDK fixtures still test generic bounded traversal separately. Broader #13/#35/#37/#41,
canonical query/state producers under #48, UX under #56, producer-result persistence, general
EvidenceTrace, production authentication/HA/deployment and controlled recomputation remain open.
