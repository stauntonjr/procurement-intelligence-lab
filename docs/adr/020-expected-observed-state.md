# ADR-020: Govern expected and observed procurement state separately

Status: accepted

## Context

The existing operational projection captured only resolved BOM lines. It could not distinguish a requirement from an order, receipt, substitution, delay, partial observation, or missing observation. Anomaly detection needs explicit comparable state rather than inferring it from raw lines.

## Decision

Model expected requirements and observed procurement records as separate immutable projections.

- `StateScope` binds each record to tenant, project, site, and BOM revision.
- `ExpectedRequirement` records required quantity, as-of timestamp, and source evidence.
- `ObservedProcurement` records ordered, received, substituted, delayed, and unknown quantities, freshness, as-of timestamp, and evidence.
- `ExpectedObservedState` pairs the two projections and deterministically exposes outstanding quantity and observation freshness.

This is a governed projection, not canonical source truth. It does not perform anomaly detection, prediction, or external integration. Those concerns remain separate slices.

## Consequences

Deterministic anomaly detection can compare explicit expected and observed inputs while preserving scope, evidence, and as-of context. Future adapters must populate observed records through scoped, append-oriented inputs; they may not infer authorization or source evidence from untrusted documents.
