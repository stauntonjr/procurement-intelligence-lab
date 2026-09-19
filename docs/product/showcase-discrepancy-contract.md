# Showcase required-quantity discrepancy contract

**Policy:** `procurement-governing-claims/v1`

**Scope:** `synthetic-tenant` / `synthetic-project` / `synthetic-site`

**Query as-of:** `2026-01-15T00:00:00+00:00`

**Canonical item:** `GPU-A`

**Predicate:** `required_quantity`

**Unit:** `each`

This is the frozen, synthetic acceptance contract for the evidence-inspector discrepancy
scenario. It supplies application inputs and literal reference outcomes separately; runtime code
does not read this file.

## Source artifacts

| Revision fixture | SHA-256 | Source location | Asserted quantity |
|---|---|---|---:|
| `showcase_bom_revision_a.xlsx` | `818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8` | `BOM!C2` | 4 |
| `showcase_bom_revision_b.xlsx` | `c12a72195c783343e24a05eb77ba9cb0145b889f5b39a66cc449d247c29bfdf2` | `BOM!C2` | 6 |
| `showcase_bom_revision_b_equal.xlsx` | `818f93274d15859ca11b2f47d2b1ffff192a50712354150414d12fcff37f8fd8` | `BOM!C2` | 4 |

Every fixture row also cites `A2:E2`; those cells establish the item identity, description,
quantity, price text, and unit visible in the inspector. The policy uses quantity and unit only
for the required-quantity decision.

## Frozen scenarios

| Scenario ID | Candidate conditions | Expected decision |
|---|---|---|
| `conflict` | Revisions A and B are approved and effective, with no explicit supersession. | `unresolved`; no required quantity; both candidates retained as conflicting evidence. |
| `superseded` | Revision B is approved, effective on 2026-01-10, and explicitly supersedes A. | `governed`; 6 `each`; B governs and A remains retained as superseded evidence. |
| `shared_value` | Revision A and `B-equal` are approved and effective, without supersession. Both assert 4 `each`. | `governed_shared_value`; 4 `each`; both candidates jointly govern. |
| `missing_approval` | A's effective interval ended on 2026-01-10. B is effective thereafter but has no approval record. | `unresolved`; no required quantity; A is stale and B is ineligible. |

Document time is `2025-12-31T00:00:00+00:00` and ingestion time is
`2026-01-02T00:00:00+00:00` for all candidates. They are retained as provenance and do not select
a winner. Approval occurred at `2026-01-01T00:00:00+00:00` where present.

## Browser contract

The `scenario` query parameter selects only the four scenario IDs above. The `/api/ask` response
contains the policy ID, as-of time, candidate revision metadata, dispositions, all candidate
EvidenceRefs, and either a governed value or explicit abstention. `/api/source` accepts an admitted
EvidenceRef ID under the normal scope check and renders the original row from the matching fixture.

The browser displays the service decision. It does not select a revision, infer a supersession,
perform numeric reconciliation, or treat a later document/ingestion time as authority.
