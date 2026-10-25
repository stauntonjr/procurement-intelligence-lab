# ADR-020: Govern expected and observed procurement state separately

Status: accepted

## Context

The existing operational projection captured only resolved BOM lines. It could not distinguish a requirement from an order, receipt, substitution, delay, partial observation, or missing observation. Anomaly detection needs explicit comparable state rather than inferring it from raw lines.

## Decision

Model expected requirements and observed procurement records as separate immutable projections.

- `StateScope` binds each record to tenant, project, site, and BOM revision.
- `ExpectedRequirement` records required quantity, as-of timestamp, and source evidence.
- `ObservedProcurement` records ordered, received, substituted, delayed, and unknown quantities, freshness, as-of timestamp, and evidence.
- `ExpectedObservedState` pairs the two projections and deterministically exposes outstanding quantity and observation freshness. For a scope and canonical key, comparison selects the latest observed record at or before the requested as-of time; records in another scope or after the cutoff do not pair.

This is a governed projection, not canonical source truth. It does not perform anomaly detection, prediction, or external integration. Those concerns remain separate slices.

## Intrinsic construction boundary (#118)

Expected and observed constructors enforce finite nonnegative Decimal quantities, required evidence
and a timezone-aware as-of value independently of application paths. Awareness requires both a
`tzinfo` and a non-None UTC offset; offsetless timezone objects are naive. Both public projection/
comparison helpers validate this same cutoff even for empty inputs. Invalid time raises the existing
`TemporalContractError`, preserving ValueError compatibility. Valid offsets are retained.

Pairs require matching canonical key and every StateScope field. Different record timestamps remain
valid. Zero, fractional quantities, partial/missing observations and overages remain representable;
there is no constructor constraint requiring received or other observed components to fit within an
ordered quantity. Overage classification belongs to anomaly policy. A missing observation remains
None with UNKNOWN freshness. Existing outstanding arithmetic and latest-in-scope/as-of selection
are unchanged. C008 protects quantity/pair invariants; C031 protects actual timestamp awareness.

## Consequences

Deterministic anomaly detection can compare explicit expected and observed inputs while preserving scope, evidence, and as-of context. Future adapters must populate observed records through scoped, append-oriented inputs; they may not infer authorization or source evidence from untrusted documents.
