# ADR-044: Atomically retain completed planned prefixes with their source evidence

Status: proposed, decision [#228](https://github.com/stauntonjr/procurement-intelligence-lab/issues/228),
primary M2, parent #37. Implementation is not authorized by this proposal.

## Context

ADR-043 / PR #227 executes the actual five-stage prefix and binds its complete plan, resolved
references, typed outputs and twelve dispositions in an ephemeral receipt. ADR-038 archives
DocumentSnapshot/source bytes, but that snapshot does not retain the physical plan or execution
receipt. Calling the current archive alone would lose the distinction between planning metadata,
actual prefix execution and later NOT_EXECUTED declarations.

## Proposed decision

Add a separately invoked completed-prefix archive capability, `planned_prefix_archive/v1`, beside
unchanged source/review/dependency storage. A neutral frozen record binds the actual
PrefixExecutionReceipt to its exact existing DocumentSnapshot and normalization parameters.
An injected port atomically retains source bytes, snapshot/claim membership and this binding.
Postgres owns transactions and additive capability tables; bootstrap owns codec registrations.
The platform runner and declarative package remain independent of storage and procurement.

Use exact scope plus execution_digest as the computation key. Compare canonical computation
content and captured bytes on every retry, not just the hash. Repeated computation may have a
different server completed_at; retain the first committed full receipt and sequence. Only that
completion timestamp is excluded from computation comparison. Any other differing retained
content under the same key conflicts. This selects persistence evidence, never governing claims.

Every new invocation still executes five stages. Default ephemeral execution is unchanged;
opt-in archival output distinguishes the current execution receipt from the retained first
receipt. Reads reconstruct retained evidence without source access or executor invocation.
There is no attempt journal, lookup-before-execution cache, request deduplication or exactly-once
processing guarantee. Commit acknowledgement can be ambiguous; never claim a failure proves
that no transaction committed.

Require explicit capability initialization and preflight runtime plus storage readiness before
source I/O. No success output is emitted until atomic retention acknowledges completion. Scope,
source/claim/mention lineage, policy content and twelve-stage dispositions remain exact on read.
Reuse appropriate typed execution/archive failures; driver details and DSNs stay private.

The existing codec does not admit bytes, while PhysicalPlan retains canonical_json bytes.
Add a strict bounded bytes-hex scalar and explicit record/enum registrations for the new graph.
Preserve existing DocumentSnapshot encodings, hashes and old-reader compatibility; new roots
remain confined to the new capability. No pickle or class imports driven by stored data.

## Alternatives and consequences

- Adopt RESOLVE first: advances execution coverage but also needs explicit candidate/threshold,
  abstention/review and benchmark acceptance under #14; it does not retain the existing plan.
- Add generic jobs/attempts under #36: substantially larger lifecycle and authority decisions.
- Store a receipt sidecar in a second transaction: rejected because it can expose an archive
  without its execution binding or vice versa.

The recommendation reuses existing source history while adding a port, codec support, capability
and public read boundary. First-retention semantics must be visible: a later successful execution
can have a different current receipt digest while referencing the same retained receipt.
Broader #13/#35/#36/#37/#12/#75 acceptance, later stages and production operations remain open.
The [written proposal](../superpowers/specs/2026-10-21-planned-prefix-archive-design.md) defines
the exact scope and evidence required before a separately reviewed implementation plan.
