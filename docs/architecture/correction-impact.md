# Declared dependencies and correction impact

Issue #218, ADR-040, M2 under #41/#35/#37. This follows the immutable [document review](document-review.md).
It identifies potentially affected **registered references**, not verified changed answers.

A DependencyManifest contains exact StateScope/version, command request_id, archived roots
(snapshot/assertion IDs), and canonically ordered ClaimDependency records. Each reference names
an explicit output of a supplied TransformationEvent. Data inputs are USED_INPUT/DERIVED_FROM;
USED_SCHEMA/USED_MODEL remain metadata. Parent-event order never implies data dependence. Every
data input must be a root or a registered output; ambiguous producers, duplicate IDs/inputs,
missing inputs, cycles and source/output collisions fail typed. Producer receipts retain full
implementation/context metadata and fixed-offset time; raw environment entries are unsupported.
Limits are128 roots,256 references and32 data inputs per producer. The input is a declaration from
a trusted producer, not proof of execution, scientific quality or complete consumer registration.

The additive Postgres dependency schema1 stores a frozen DependencySnapshot with trusted recorder,
server time, policy declared-dependencies/v1 and full-content SHA256. Request identity is scoped;
exact retries retain the first snapshot/time and changed content/actor conflicts. Original archive1
and review1 remain unchanged. SQL append guards, exact root foreign keys, strict typed DAG decoding,
payload/content hashes and source-integrity checks protect the supported trusted local boundary.
They do not claim adversarial database-owner or production authentication guarantees.

Initialize after archive init, using the same private PIL_ASSERTION_ARCHIVE_DSN and the installed
storage extra. Set PIL_DOCUMENT_REVIEWER_ID at the trusted local shell boundary. It supplies recorder
identity, never the producer manifest. Registration APIs require REVIEW plus READ_EVIDENCE before I/O;
inspection requires READ_EVIDENCE and matching request scope. No operational-agent tool is added.

```bash
uv run --extra storage python -m procurement_intelligence_lab.interfaces.correction_impact init
uv run --extra storage python -m procurement_intelligence_lab.interfaces.correction_impact \
  register --scope scope.json --input producer-manifest.json
uv run --extra storage python -m procurement_intelligence_lab.interfaces.correction_impact \
  inspect --scope scope.json --snapshot-id '<dependency_snapshot_id>' \
  --task-id '<approved review task_id>' --as-of '2026-10-20T23:00:00+00:00' --max-depth 8
```

`producer-manifest.json` is registered typed DAG JSON emitted by the SDK's
`bootstrap.archive_codec().dumps(DependencyManifest(...))`. The manifest root must be exactly
DependencyManifest, not a DependencySnapshot or arbitrary JSON. SDK authors supply actual retained
TransformationEvent receipts with explicit output/input IDs; root and reference tuples are sorted
by assertion_id/reference_id. No arbitrary downstream value is accepted or stored. The1MiB input
boundary rejects unsupported records, duplicate/unreachable/malformed graphs, excessive nesting,
invalid Unicode, client recording identity/time and scope mismatches. Typed stderr JSON/exit2
covers input, policy conflict, not-found, integrity/unavailable and authorization failures.

Inspection requires an exact dependency snapshot and a visible APPROVE decision as of the aware,
fixed-offset timestamp. Missing/future snapshots or tasks, pending/rejected decisions and source
roots outside the manifest fail typed. Original review/domain admission is rechecked. No implicit
"latest graph" or "latest approved correction" selection occurs.

Breadth-first traversal has explicit depth1..32 and returns each affected reference once at minimum
depth, all declared data links within the visited subgraph, and sorted omitted frontier references.
Reports retain exact source/review evidence and snapshot digest, producer event/provenance IDs,
policy and as-of. `potentially_stale: true` means this dependency may require review/recomputation;
even an equal-value approval is conservatively included. This is not a proven numeric change.

Every result, including empty downstream registrations, states `coverage: registered_graph_only`
and `global_completeness: not_evaluated`. `traversal_complete` describes only traversal of this
declaration. `recomputation_executed` and `governing_state_updated` stay false. No source assertion,
review, downstream output or projection freshness is changed. The supplied graph is closed, but
unregistered consumers are unknown. There is no graph database, execution planner, new logical
stage or general EvidenceTrace API completion.

Acceptance includes core diamond/empty/cycle/missing/boundary oracles, real Postgres atomicity/replay,
actual subprocess and parser paths, and a clean installed archive -> review -> declared SDK fixture
-> restarted bounded impact probe. Fixtures demonstrate registration/traversal only; existing
procurement downstream producers have not yet been wired to emit these receipts. Actual producer
adoption and policy-controlled invalidation/recomputation are the next boundaries. Broader
#13/#35/#37/#41/#56/#63 remain open, with production authentication/HA/UI/deployment separate.
