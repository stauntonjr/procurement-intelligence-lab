# ADR-026: Qualified anomaly assessment and append-only lifecycle

Status: accepted

## Context

ADR-016 introduced the anomaly taxonomy and deterministic helpers. ADR-020 separated expected and
observed state, and ADR-023 established predicate-specific governing claims. The existing state
orchestrator nevertheless treats an absent observation as a missing purchase order and compares
revision labels without authority ordering. An empty anomaly tuple also cannot distinguish a clear
comparison from one that was impossible to assess. The lifecycle enum names review states but does
not define an auditable transition history.

## Decision

Adopt [`procurement-anomaly-assessment/v1`](../product/anomaly-assessment-v1.md).

- Procurement owns input qualification, per-kind policy, and comparison orchestration.
- Every requested kind returns an explicit `anomaly`, `clear`, `not_assessed`, or `not_applicable`
  result with reason, role-specific evidence, input identities, scope/as-of, and canonical policy
  configuration digest.
- Missing PO requires positive evidence of current, complete, authoritative coverage. Source
  silence does not establish absence.
- Quantity aggregation deduplicates exact assertion replays, sums independently identified eligible
  lines, and abstains on ambiguous duplicates, competing versions, unit conflicts, or incomplete
  coverage.
- Revision staleness requires an explicit applicable supersession path. Unequal labels alone do not
  order revisions.
- Price, schedule, substitution, identity, and coverage comparisons retain their own eligibility;
  failure to assess one kind does not block a qualified independent kind.
- Policy configuration, not only its human-readable ID, participates in assessment provenance and
  identity. The established generic `Anomaly.anomaly_id` formula remains compatible.
- The platform owns a pure lifecycle reducer over append-only events. Events reference one exact
  anomaly and predecessor; replay is idempotent only for byte-equivalent event meaning.
- Public acceptance is read-only and fixture-backed. No web mutation authority is introduced.

Structurally invalid input fails with existing typed contract errors. Missing or conflicting
business evidence produces a typed assessment disposition.

## Consequences

Callers can distinguish a verified clear comparison from abstention, audit policy changes, and
replay review state without overwriting source or detection evidence. The unsafe absent-observation
and unequal-revision behaviors become regression challenges. More input qualification is required,
but it remains deterministic and domain-owned.

This decision does not define general human-review authorization, identity/relationship policy,
scenario costing, forecasting, recommendations, external actions, persistence, or production
source authority. Those remain governed by Issues #41, #44, #52, #61, #65, and separately scoped
adapter decisions.
