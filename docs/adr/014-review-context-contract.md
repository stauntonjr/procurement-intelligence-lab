# ADR-014: Review context is a reproducible claim reference

Status: accepted

## Context

The chat and evidence inspector need to let a user report a wrong result or source problem without asking the user to reconstruct the execution manually. Stable claim, evidence, and trace identifiers now exist, but the application needs a typed bundle that identifies what should be reviewed.

Persistence and raw feedback capture are intentionally later concerns. This slice must not imply that a review report has been stored.

## Decision

Expose a read-only review-context contract containing:

- the material claim ID, kind, value, and epistemic status;
- the evidence IDs supporting the claim;
- the execution-chain and node IDs;
- a fixed set of allowed review reasons: wrong result, source issue, mapping issue, resolution issue, and stale result.

The HTTP adapter exposes this as a preview at `/api/review-context?claim_id=...`. It returns references and review affordances, not user-authored feedback or a persisted report.

## Consequences

The future chat UI can start a review flow with complete reproducibility context. A later product-signal service may append the user's reason and detail to this context, subject to privacy and triage policy. Unknown claims fail closed with a not-found response.

Adding review reasons or changing the context fields is a public contract change and requires corresponding tests and documentation updates.
