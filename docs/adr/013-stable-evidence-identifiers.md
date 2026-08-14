# ADR-013: Stable identifiers for evidence navigation

Status: accepted

## Context

The inspector, future source viewer, review workflow, and product-feedback loop need to refer to the same claim and evidence objects across requests. Display labels and array positions are not durable references. Persistence is not yet part of the repository, so identifiers must be useful before a database exists.

## Decision

Use deterministic, opaque identifiers derived from semantic provenance:

- `EvidenceRef.evidence_id` identifies an artifact location and its content hash.
- `EvidenceNode.node_id` identifies a stage, status, and its evidence references.
- `EvidenceChain.chain_id` identifies a claim trace and ordered nodes.
- `EvidenceBackedClaim.claim_id` identifies the claim kind, value, status, trace, and evidence.

Identifiers are produced by a framework-independent hashing helper. They are stable for identical semantic inputs and change when the referenced evidence or claim context changes. They are navigation and correlation identifiers, not database primary keys or authorization credentials.

## Consequences

The HTTP inspector can expose references that a source viewer or feedback report can retain without copying source contents. The identifiers remain deterministic in tests and local demos. A future persistence layer may store them as natural correlation keys, but may introduce separate database identities if lifecycle or tenancy requires them.

Changing the canonical serialization inputs is a compatibility change and requires an ADR or amendment. Identifiers must not be used to infer authority: provenance, epistemic status, and review state remain separate fields.
