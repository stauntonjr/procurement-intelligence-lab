# ADR-040: Retained dependency declarations and bounded correction impact

Status: accepted

Issue #218 follows ADR-039 under #41/#35/#37. The durable source archive has no record of
consumers beyond ASSERT. Inferring dependencies from shared evidence cells or selecting a
new governing claim would invent semantics. A graph database would add mechanics before a
producer/consumer contract exists.

Retain immutable, scoped dependency manifests behind a port. Each archived assertion root is
pinned to an exact snapshot; each downstream reference names a supplied TransformationEvent
that lists that reference as an output. Only USED_INPUT and DERIVED_FROM edges imply data
dependence. Schema/model links and parent-event order do not. This is execution-instance
lineage, not domain configuration or a change to ADR-022's fixed logical topology.

The trusted producer declares the receipts. Registration validates portable metadata,
closed input membership, unique identities, acyclicity and archive membership; it does not
verify execution, store downstream values, or assert global consumer coverage. Reports always
say registered_graph_only and global completeness not_evaluated, including empty graphs.

A read-only query binds an exact visible approved review, source root and dependency snapshot.
Its breadth-first traversal reports potentially affected references, all declared dependency
edges between visited references, and any omitted frontier at an explicit depth bound. It
never changes freshness globally, rewrites source facts, selects authority, invalidates a
projection or executes recomputation. Potential impact is deliberately conservative even for
an equal-value correction. Controlled recomputation and real downstream producer adoption
require subsequent policy and acceptance evidence.

Explicit additive Postgres dependency schema1 leaves archive1/review1 intact. Exact command
retries retain original identity/time; changed commands conflict. Stored graphs, hashes and
source membership are revalidated. A separate trusted local CLI owns registration identity;
application writes require REVIEW plus READ_EVIDENCE, reads READ_EVIDENCE and exact scope.
No operational-agent permission, graph-retrieval adapter, production authentication or general
EvidenceTrace completion is implied. Missing/foreign/future/unapproved/corrupt inputs fail typed.
