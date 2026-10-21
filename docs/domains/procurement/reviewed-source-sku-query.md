# Explicit reviewed source-SKU replay

Issue #223 implements the policy approved in #222 / ADR-042. Start with the immutable
[archived source query](archived-source-sku-query.md) and [document review](../../architecture/document-review.md).
Approval itself never changes that query or starts work. This separate trusted local caller
executes a new view over exactly the selected approved SKU corrections.

With archive1, review1 and dependency1 initialized, explicitly add the versioned capability:

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.correction_impact init-reviewed
```

This creates immutable `approved_correction_roots/v1` capability metadata and membership tables.
It does not update existing immutable version records or migrate source/review/dependency payloads.
Ordinary operations never initialize it. Archive-only declarations and reads still work without
review tables or this capability. Missing capability/reader fails typed, never as an empty graph.

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.reviewed_bom_query \
  --scope scope.json --snapshot-id '<exact archived snapshot>' \
  --reviews selected-reviews.json --as-of '2026-10-21T18:00:00+00:00' \
  --request-id 'reviewed-skus-1' --context query-context.json
```

Selection JSON has exactly `{"task_ids":["<approved task ID>"]}`. Context has exactly run_id,
code_revision and aware fixed-offset started_at. Both files are strict UTF-8 JSON bounded to32KiB;
duplicate keys/IDs, extra fields, nested/malformed values and invalid Unicode fail explicitly.
Set the existing private PIL_ASSERTION_ARCHIVE_DSN and trusted PIL_DOCUMENT_REVIEWER_ID. This
local manifest/identity boundary is caller-pinned, not production attestation or authentication.

Application execution requires REVIEW plus READ_EVIDENCE and matching scope before database I/O.
Every selected approval must be visible at inclusive as-of and refer to a SKU assertion in the
exact source/version. Source/approval <= as-of <= execution <= registration; the server samples
registration after actual computation. Pending/rejected/future/foreign/non-SKU reviews fail typed.
Selecting two tasks for one assertion fails, even if the proposals agree. Selection order does
not choose a winner. Other approvals remain `unselected_reviews: not_evaluated`.

Each actual row application consumes the original assertion and a typed approved-correction data
root, validated against the retained journal. The final set query consumes original unselected
row references and reviewed-row outputs. Review values are not hidden in metadata. At32 corrected
SKU rows this is64 roots/33 producer references, with at most32 data inputs on any producer.
Empty sources/selections and unsupported counts fail; no truncation or batching policy is invented.

Correcting one of two GPU-A rows to GPU-B yields GPU-A and GPU-B. Exact strings/case variants
remain distinct; canonical identity and quantities/prices are not computed. A selected proposal
may resolve a missing SKU or introduce null. Any remaining missing/blank value makes the complete
result null/unresolved with separately labeled known strings. Complete reviewed results are
inferred, not observed in the original file or governing truth. Equal-value approvals still
produce new evidence identity without claiming a changed numeric/business answer.

Output retains source evidence, complete selected review histories, actual row/query events and
the dependency receipt. References bind full retained review content/digest, as-of encoding and
execution metadata. Exact source/selection/as-of/context/request/actor retries return the first
receipt/time and the same replayed result; changed reused commands conflict without a second
registration. Values are reproducible, not materialized in a new result cache.

`recomputation_executed: true` describes this selected-view execution only. Original source/query
values, bytes, approvals and governing state remain unchanged. Generic correction impact stays
conservative even for a view that incorporated that correction. Coverage remains
registered_graph_only/global_completeness:not_evaluated; no globally fresh/current result,
automatic scheduler, operational-agent authority, general EvidenceTrace completion or deployment
is implied. Broader #13/#35/#37/#41/#46/#48/#56/#63 remain open.

The caller preserves source-query/review/dependency/scope typed failure envelopes. CLI failures
emit sanitized stderr JSON and exit2, with no partial-success stdout or raw backend details.
Acceptance covers domain/real Postgres/public subprocess paths and clean installed wheel replay
after source deletion, explicit initialization, retry, source export and original-query preservation.
