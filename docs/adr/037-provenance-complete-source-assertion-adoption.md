# ADR-037: Adopt provenance-complete source assertions without resolving identity

Status: accepted for Issue #211, a bounded adoption of #33.

## Decision

Extend SourceAssertion with optional immutable context: exact NormalizedObservation, captured
Artifact, upstream normalization batch/event, injected recording time, assertion component
provenance and an explicit confidence diagnostic. Source document version is the immutable content
hash; a caller-declared source version remains separately nullable. Unknown confidence is reported
as not estimated, never a synthetic score. Context and field evidence must agree intrinsically.

Context-bearing assertions admit null only through an unresolved observation with a diagnostic.
Legacy assertions without context retain their established identifier calculation. Rich assertions
use a separate versioned identity namespace including typed value and context; this prevents
context loss or string/number collisions from masquerading as the same claim. Null without context
is invalid, including the prior runtime admission gap covered by regression challenge C030.

Keep AssertStrategy's existing signature. Application composition supplies a per-run factory
parameterized by immutable origin metadata; bootstrap selects the procurement implementation.
The factory is runtime dependency injection, not an executable callback in a DomainPackage.
Alternatives were changing every strategy caller to carry parser-specific metadata, or retaining
metadata only in an application wrapper. Both weaken the existing boundary or the claim itself.

The assertion's transformation_event_id points to its upstream NORMALIZE event, as legacy
assertions point to their upstream STRUCTURE event. A separate ASSERT event lists the assertion,
mention and batch receipt IDs as outputs and NORMALIZE as its parent. No event/assertion identity
cycle is introduced. Source evidence and assertion component provenance remain distinct.

The BOM strategy emits one claim per observation. Missing and unmapped fields become explicitly
unresolved null claims, with a fixed unmapped-field predicate and the original raw field retained.
Source-row hints keep duplicate/conflicting rows separate. EntityMention text comes only from
nonblank SKU evidence; missing SKU yields no fabricated mention and a visible diagnostic. A mention
does not establish canonical identity. Conflicting claims are never reconciled in this stage.

The five-stage diagnostic CLI opts in with --assertions and requires explicit normalization
policy. Existing three/four-stage outputs remain compatible. Header-only input emits a truthful
empty ASSERT receipt; it does not invent an assertion. In-memory ledger append preserves rich
records and conflicting claims, but no CLI persistence, durable storage or exactly-once replay is
added. #33/#13/#35/#37 retain broader acceptance, and the physical planner remains planning-only.

## Validation

Contract tests cover context construction, missing/unmapped values, duplicates/conflicts,
scope/version/time, stable identities, legacy ID compatibility and append retention. Tests exercise
the actual CLI and clean installed wheel, three/four/five modes, error envelopes and source-cell
drill-down. Nine-source gold checks claims, mentions and attached evidence separately. Required
full checks, coverage ratchet and public challenge/mutation checks apply to the latest revision.
