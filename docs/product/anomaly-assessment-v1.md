# Qualified anomaly assessment v1

## Purpose

`procurement-anomaly-assessment/v1` defines deterministic, evidence-backed comparison of a
governed procurement requirement with admitted observations. An assessment is neither a forecast,
a recommendation, an approval, nor an external action. It records what could be evaluated as well
as what could not.

## Request identity and authority

Every assessment request names one tenant, project, site, BOM revision, canonical item, and
timezone-aware as-of instant. Expected values come from a retained governing-claim decision under
`procurement-governing-claims/v1`. Observations are admitted only when their scope, effective time,
approval state, source identity, and evidence are explicit.

Revision labels are source metadata. They are not sortable authority and do not replace the
governed projection version. Empty source material proves absence only when a current, authoritative
coverage attestation explicitly says the relevant population was completely observed.

## Result contract

The service returns one `AnomalyAssessment` for every requested anomaly kind:

| Status | Meaning |
|---|---|
| `anomaly` | Qualified evidence establishes a deviation and the result contains an open anomaly. |
| `clear` | Qualified evidence supports the comparison and it is within policy. |
| `not_assessed` | Missing, conflicting, stale, future, cross-scope, or unresolved evidence prevents comparison. |
| `not_applicable` | The kind does not apply to the admitted subject under the requested policy. |

An empty anomaly list is not proof of a clear result. Each result retains its kind, status, optional
reason, scope, as-of instant, subject and input identities, role-specific evidence, policy ID,
canonical per-kind policy configuration and digest, and optional anomaly. Evidence roles are
`requirement`, `observation`, `governance`, `coverage`, `planned_price`, `committed_price`,
`required_schedule`, `commitment`, `supersession`, `relationship`, `resolution`, and `lifecycle`.
The anomaly envelope retains the unique flattened evidence set for compatibility.

Structurally invalid values raise the existing typed semantic, scope, or temporal contract error.
Legitimate uncertainty returns `not_assessed`; it is not an exception and is never converted to
zero.

## Qualification and comparison matrix

| Kind | Qualified input | Anomaly rule | Required abstention |
|---|---|---|---|
| `missing_po` | Positive governed requirement plus current, complete, authoritative PO coverage for the exact scope/item/as-of | No applicable approved PO line and requirement is strictly above the configured minimum | Missing/incomplete/stale coverage, unresolved requirement, ambiguous duplicate, or unknown eligibility |
| `quantity_mismatch` | Governed requirement and independently identified eligible PO lines in one unit | Absolute difference between required and summed ordered quantity is strictly greater than tolerance | Unit conflict, incomplete coverage, unresolved requirement, competing line versions, or unknown quantity |
| `coverage_gap` | Explicit coverage/freshness evidence | Coverage is incomplete or stale according to policy | Missing coverage evidence is `not_assessed`, not a gap inferred from silence |
| `substitution` | Evinced, approved, unambiguous substitute relationship distinct from identity plus substituted quantity | Substituted quantity is strictly above tolerance | Similarity alone, missing relationship evidence, or unapproved/ambiguous relationship |
| `stale_revision` | Applicable observed revision plus authoritative, unambiguous supersession edge/path effective at as-of | Governed revision explicitly supersedes the observation | Unequal or lexically ordered labels without an edge; future/ambiguous/non-authoritative supersession |
| `price_deviation` | Governed planned and committed unit prices with identical currency, unit, and basis | Absolute difference is strictly greater than the currency-unit tolerance | Missing/conflicting basis, currency/unit mismatch, or stale/future price |
| `late_commitment` | Evinced required-by date and supplier-confirmed, unconflicted commitment effective at as-of | Commitment is later than required-by plus tolerance | Missing required-by, missing confirmation, future approval, superseded or conflicting commitment |
| `unresolved_identity` | Explicit unresolved or ambiguous resolution decision and mention evidence | Decision remains unresolved for the assessed mention | No fabricated canonical key; resolved decisions are clear |

Exact tolerance equality is clear. Quantities and prices use finite, non-negative `Decimal` values.
Dates and durations are explicit; no FX, unit conversion, quote fallback, or delivery prediction is
performed.

## Multiplicity, ordering, and replay

Distinct eligible PO lines sum. Exact assertion replay, identified by the same source assertion ID
and content, contributes once. Divergent content under one assertion ID and competing effective
versions are conflicts and cause the affected kind to abstain. Input and evidence order never
changes the result. Other-scope and future records are rejected with retained dispositions and
never participate in totals.

Each immutable per-kind policy has a nonblank policy ID and validated configuration. Canonical
serialization preserves Decimal, date, duration, booleans, and sorted unordered IDs. Its digest is
part of decision provenance and assessment identity, so two configurations sharing a display ID do
not alias. Installation location and detection wall-clock time do not change semantic identity;
scope, as-of, governing decision, inputs, evidence, or policy configuration do.

## Lifecycle

Detection creates an immutable `OPEN` anomaly. Lifecycle state is projected from append-only
events; events never alter the detection or source ledger.

| Current | Permitted next states |
|---|---|
| `OPEN` | `IN_REVIEW`, `SUPPRESSED`, `RESOLVED` |
| `IN_REVIEW` | `OPEN`, `SUPPRESSED`, `RESOLVED` |
| `SUPPRESSED` | `OPEN`, `IN_REVIEW`, `RESOLVED` |
| `RESOLVED` | `OPEN` with explicit reopening evidence |

Every event names the exact anomaly, previous and new state, actor, timezone-aware timestamp,
reason, evidence, policy, and expected prior event. Suppression requires all of those fields.
Resolution requires adjudication or comparison evidence; an empty detector result is insufficient.
Exact event replay is idempotent. Divergent reuse of an event ID, a stale predecessor, self or
illegal transitions, and cross-anomaly application fail closed. Recomputed assessments have their
own anomaly identities and never inherit prior suppression implicitly.

## Public and ownership boundary

The application service authorizes request scope and injects policy and time; procurement domain
code qualifies and compares; the platform owns the generic anomaly envelope and lifecycle reducer;
adapters load and retain records without deciding meaning. The public inspector may display
synthetic assessments and fixture-backed lifecycle history, but grants no mutation authority.

Issue #41 owns general review/correction workflows, #44 relationship semantics, #52 scenario
costing, #61 forecasting, and #65 decision support. This contract creates no ERP ingestion,
receipt accounting, database rollout, public write path, or autonomous remediation.

## Conformance corpus

[`evals/anomalies/v1/manifest.json`](../../evals/anomalies/v1/manifest.json) is the versioned
synthetic corpus. Every case names exact status, reason, evidence IDs, scope, as-of, and source
content digests. Runtime and public-boundary tests must consume the corpus rather than reconstruct
unqualified quantities in helper-only contexts.

## Reference acceptance path

The read-only inspector exposes fixture-backed examples for qualified missing PO, incomplete
coverage, price deviation, late commitment, stale revision, substitution, unresolved identity,
and quantity-mismatch lifecycle projections in `OPEN`, `IN_REVIEW`, `SUPPRESSED`, and `RESOLVED`
states. The response keeps assessment status separate from projected lifecycle status and includes
the canonical policy configuration/digest, scope/as-of, input and governance IDs, role-specific
evidence, and lifecycle reasons. Every JSON corpus or lifecycle reference resolves through the
same `/api/source` boundary as the existing XLSX evidence.

These examples admit only committed fixture values. Query-string business values cannot replace
the governed requirement or observations, and the HTTP service has no lifecycle mutation route or
write controls. The installed-wheel probe repeats these scenarios outside the checkout and checks
their packaged records and source links.
