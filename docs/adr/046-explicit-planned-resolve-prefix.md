# ADR-046: Explicit planned RESOLVE prefix with pinned identity evidence

Status: proposed; owner selected RESOLVE direction on 2026-10-24. Written design is pending
approval. Decision [#235](https://github.com/stauntonjr/procurement-intelligence-lab/issues/235),
primary M3, parent #14. [Proposed design](../superpowers/specs/2026-10-24-planned-resolve-prefix-design.md).

## Context

ADR-043/044/045 deliver actual INGEST-through-ASSERT execution, atomic completed-prefix retention
and durable local jobs. RESOLVE is declared but remains NOT_EXECUTED. The legacy normalized-exact
resolver has no adapter tying adopted row-grounded mentions to a pinned candidate catalog and
actual planned execution. Source assertions are evidence; an identity link is a separate explicit
decision and cannot imply reconciliation authority.

## Proposed decision

Add a separate opt-in six-stage profile on the same fixed topology and planner. Reuse the real
first-five runner and invoke one registered ResolveStrategy. Supply an explicit immutable,
exact-scope, as-of candidate snapshot and procurement-owned internal-SKU policy. No implicit
catalog, auto-created canonical entities, alias matching, scoring/model swap or future-state
selection. Unique normalized match resolves; no match or collisions abstain. Bind each outcome
to the exact source mention and its HAS_SKU row evidence rather than the legacy subject-text
evidence lookup. Only resolved rows may receive canonicalized assertion links.

Platform owns typed input/output/receipt/admission contracts without importing procurement;
procurement owns namespace policy and the existing deterministic matching adapter; bootstrap
injects catalog/policy/executors/storage/clock. A complete resolution batch and actual sixth event
remain visible even for an empty document. Retain every outcome and candidate snapshot, not only
winners. Missing/unknown identity never becomes canonical or zero.

Use new six-stage request/receipt and explicit planned_resolution_prefix/v1 archive capability.
Retain unchanged source/five-stage evidence, catalog and six-stage result in one transaction.
Preserve first retained versus current receipts and scoped recovery without the original files
or current executors. Existing ASSERT-only formats/digests/codecs/local jobs remain unchanged;
six-stage job integration is a later contract. No implicit migration or source/assertion rewrite.

## Alternatives and consequences

Silently widening five-stage v1 jobs and snapshots breaks pinned compatibility and frozen input
validation. Calling only a resolver helper fails actual pipeline/provenance acceptance. Full
governed-state adoption adds a distinct authority policy. A separate profile costs explicit
contracts, additive storage and public/artifact qualification, but exposes the exact acceptance
boundary. New algorithm or provider selection would require comparable benchmark evidence and is
not part of this proposal.

The implementation must qualify exact mention coverage, candidate collision/missing behavior,
scope/time/namespace isolation, transaction/integrity/restart behavior, public installed callers
and unchanged legacy paths. Synthetic integration metrics are bounded to the declared namespace,
not broad entity-resolution quality. #14/#42/#39/#43/#45 and broader #36 remain open. No later
stage, queue/worker, operational-agent authority or production deployment is approved by this ADR.

Owner approval of the written design precedes implementation planning and product code. Approval,
builder review or documentation checks alone establish no runtime acceptance.
