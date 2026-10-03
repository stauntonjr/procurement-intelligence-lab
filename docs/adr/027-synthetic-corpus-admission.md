# ADR-027: Admitted synthetic corpus investigation

- Status: Accepted for the owner-approved corpus plan; implementation pending
- Date: 2026-10-03
- Primary issue: #29; related #12, #27, #32, #48, #71

## Context

The legacy inspector demonstrates a few fixed examples. A richer demo needs a generic scoped
item/date investigation, original source inspection, and independently evaluated outcomes.
Adding rows alone does not establish retrieval quality or production representativeness.

## Decision

Keep the legacy fixtures and routes unchanged. Introduce a read-only corpus port whose frozen
records contain parsed values, raw scope, authority metadata and evidence references. Ports do
not import procurement or adapter types. A filesystem adapter validates the versioned manifest,
relative paths, unique identities, hashes, source schema, units and finite nonnegative quantities.
Only the application composes these records into existing governance and qualified assessment
inputs. The complete admitted scoped item inventory is the policy input, never a top-k subset.

Quantity evidence resolves to original XLSX cells. Authority evidence resolves to immutable,
hash-pinned JSON records through RecordLocation. Snapshot identity includes the manifest and
all admitted workbook and authority bytes. Source lookup revalidates admission and does not
accept arbitrary paths. Scope is checked before lookup and before remapping observations to the
governed projection version (ADR-024).

Use ADR-023 approval, effective intervals and explicit BOM supersession. Use ADR-026 order-line
identity and conflict rules. Successive order snapshots have no implicit replacement rule:
independently identified lines can sum; conflicting assertions for one line abstain; exact
assertion replay deduplicates. Copying a row to another artifact changes its evidence identity.
Missing observations without coverage yield `missing_observation`, not zero or a missing-PO claim.

The server supplies the synthetic allowlisted RequestContext. Clients select only an admitted
project, item and aware cutoff. Invalid inputs are 422, unauthorized scope 403, unknown admitted
item/evidence 404, invalid admitted sources 503, and business abstentions typed 200 responses.
Reject duplicate query parameters. No actions, uploads, authentication claims, model calls,
external telemetry or retrieval ranking are introduced by this slice.

Generator specifications and evaluator gold/query/split files stay outside package resources.
Runtime artifacts contain source facts only. Gold is authored independently of production policy
and separately reviewed. Public-repository splits are development holdouts, not blind evaluation.

## Increment and consequences

First admit one synthetic project, six workbooks with forty data rows each (240 row occurrences).
Two BOM revisions, two independent order-line documents, and two non-governing documents retain
source roles explicitly. This is not the four-project G1 gate or a representative industry corpus.

Public HTTP and browser source drill-down, adversarial admission checks, temporal and numeric
boundaries, and a clean installed wheel must pass before readiness. A subsequent agent uses
this same service; models provide evidence and policies retain decision authority.
