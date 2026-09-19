# Synthetic requirement versus order comparison — Issue #60

Extend the existing read-only inspector. The authoritative requirement is the output of
`procurement-governing-claims/v1`; the order quantity is read from an explicitly admitted synthetic
order XLSX row, not inferred from a requirement. These are fixture-pinned inputs, not general PO
admission or ingestion. Scope is synthetic-tenant/project/site, requirement revision A, item GPU-A,
unit each, as-of 2026-01-15 UTC. The order observation belongs to that same scope and cutoff.

Use the existing quantity-mismatch detector with versioned policy
`procurement-showcase-order-quantity/v1`, absolute tolerance zero. Output required and ordered
quantities, assessed/mismatched or not-assessed status, fixed abstention reason, governing policy,
comparison policy, scope/as-of, typed anomaly and all source evidence. Do not calculate receipts,
outstanding delivery, missing-PO conclusions, remediation, suppression or lifecycle transitions.

| Scenario | Requirement | Order observation | Result |
|---|---|---|---|
| order_mismatch | governed 4 | recorded 2 | quantity_mismatch |
| order_matched | governed 4 | recorded 4 | matched, no anomaly |
| order_missing | governed 4 | absent | not_assessed; ordered remains null |
| order_unresolved | conflicting 4/6 | recorded 2 | not_assessed; required remains null |

Both inputs retain original-cell references. Unassessed is neither zero nor a successful match.
Repeated evaluation preserves semantic identity; input snapshots and comparison policy identify
anomaly provenance. Existing request authorization, unknown-scenario and source-ID errors retain
403/422/404 behavior. No caller-supplied quantities or timestamps are introduced. The bounded
fixtures contain one complete order observation; no duplicate aggregation, stale selection, future
selection or cross-project matching is introduced. Existing governing-policy conflict behavior is
reused. Numeric boundary tests exercise the existing detector; real HTTP and installed-wheel
checks prove the admitted fixture path. #60 remains open for its broader acceptance.
