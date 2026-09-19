# Local inspector showcase

Baseline date: 2026-09-18
Last verified: 2026-09-19

Part of [Issue #50](https://github.com/stauntonjr/procurement-intelligence-lab/issues/50).
Related contracts: Issues #15, #38, #46, #49, and #58; ADR-019; ADR-023; and the existing
claim/source HTTP endpoints. This bounded showcase slice does not by itself complete those issues.

## Contract

The browser renders `/api/ask` values, statuses, evidence references, policy-backed decision
metadata when a discrepancy scenario is selected, and recorded trace nodes.
Selecting an evidence reference sends its stable identifier and the form's explicit synthetic
tenant/project/site scope to `/api/source`. That endpoint retains authorization and fixture
lookup responsibility. The browser performs no quantity, cost, or reconciliation calculation.

The source view reads the admitted original synthetic workbook after verifying its content hash.
It renders the original XLSX headers and cell text for the selected row, highlighting only the
columns named by the EvidenceRef. Sheet, row, cells, source status, and evidence identity remain
inspectable. No PDF viewer, full spreadsheet editing, production authentication, correction
submission, or complete multi-document procurement state is claimed. Cost displays no invented
currency. Null values remain “Not established.” The browser never selects the governing revision:
it displays the service's policy ID, as-of key, candidate dispositions, and retained evidence.

New queries clear prior source/results; request sequence identifiers prevent older responses
from replacing newer query or source selections. DOM text insertion preserves untrusted text
as text. Errors clear the answer or source and provide a retry path.

## Walkthrough

1. Run `uv run python -m procurement_intelligence_lab.interfaces.web`.
2. Open `http://127.0.0.1:8000/` and submit the default GPU question.
3. Confirm **4 GPUs**, status **reconciled**, and the BOM row 2 evidence button.
4. Select that evidence. Confirm **GPU-A**, **GPU accelerator**, quantity **4**, unit price
   **100**, and cells **A2, B2, C2, D2** from `synthetic_bom.xlsx`.
5. Optionally select a recorded trace stage to filter its evidence, or inspect the full response.
6. Select **Competing approved revisions: 4 versus 6 GPUs** and submit. Confirm **Not
   established**, policy `procurement-governing-claims/v1`, the fixed as-of time, and competing
   A/4 and B/6 dispositions. Select the B source and confirm original quantity **6** from
   `showcase_bom_revision_b.xlsx`.
7. Select the shared-value scenario. Confirm **4 GPUs**, `governed_shared_value`, and both
   revisions retained as governing evidence. The other scenarios demonstrate explicit
   supersession and missing approval.

The README GIF retains three actual full-page browser screenshots: initial question, calculated
answer, and selected source. Frames pause for 3/4/7 seconds; the canvas is padded to a common
size. It is an edited walkthrough, not a latency measurement. The PNG provides a static option.

## Verification record

- Before implementation, the same browser submission produced JSON and noninteractive stages;
  no source-row action existed. This reproduced the missing public flow.
- Real-browser GPU walkthrough: expected value, status, source identity, coordinates, and original
  cells passed.
- Real-browser conflict walkthrough: an unresolved 4-versus-6 decision displayed the policy ID,
  as-of key, both retained candidates, and the original revision-B quantity 6 source row.
- Cost example: **500**, currency unspecified, two evidence rows. Selecting row 3 returned
  **CPU-A**, quantity **2**, unit price **50**.
- SKU example: **CPU-A, GPU-A**; submitting it cleared the previously selected source.
- Unsupported question: a bounded guidance message replaced the prior answer and evidence;
  selecting GPU quantity recovered successfully.
- Reconciliation-stage selection retained the relevant source link and displayed its status.
- Keyboard Enter on the source button opened the same evidence. Stopping the local demo server
  produced a clear unavailable-service message and cleared the old result; restoration and a
  fresh browser load recovered the GPU/source flow.
- At a 390-pixel viewport, the query controls and answer stacked into a readable single column;
  the source table has its own horizontal overflow container.
- The expanded real HTTP integration test follows the shipped form through ask and source,
  verifies evidence equality and quantity, and checks unknown IDs, conflicting tenant, and missing
  project scope (404/403).

Final checks: `make check` passed (252 tests, 89.54% coverage, coverage ratchet, types, lint and
architecture); `make package-smoke` built and installed `procurement_intelligence_lab-0.1.0`;
`make challenges` passed all eleven current-code oracles and rejected all eleven known-bad
mutations. HTTP checks required permission to bind localhost; the sandbox-blocked challenge
attempt was not counted as a product failure. An obsolete untracked `domain/__pycache__`
directory was moved to a temporary backup before architecture verification.

Independent review found no actionable correctness findings. Reviewed `web.py` SHA-256:
`38879c153c18a005820647d0d9a404656f03af5f8d6f1daa4ef311c71489ecd4`.
The semantic evidence artifact records the implementation commit separately. Python coverage does
not measure browser JavaScript; browser checks above are separate observed acceptance evidence.

## Recorded discrepancy packet — 2026-09-19

The [new walkthrough](showcase-walkthrough.md) supplements this historical implementation
acceptance with a continuous 2:41 recording at application revision `8829775`, all four revision
scenarios, captioned explanation, source/fixture hashes and fresh offline setup/restart evidence.
The original three-frame GIF is preserved; the README now links the 25-second discrepancy excerpt.
These artifacts do not expand the runtime contract or close the remaining umbrella issues.

## Current merged order-comparison slice

PR [#168](https://github.com/stauntonjr/procurement-intelligence-lab/pull/168) extends the
showcase with one explicitly admitted synthetic order observation. On merged `main`
(`cff0905398909fe9378dfd4f3ce4ce2f9da6895c`), the public form and clean-package path demonstrate:

- required 4 versus ordered 2: `quantity_mismatch`;
- required 4 versus ordered 4: `matched`;
- no order observation: `not_assessed` with `missing_observation`;
- unresolved required 4-versus-6 claims with order 2: `not_assessed` with
  `unresolved_requirement`.

The comparison retains separate requirement and order EvidenceRefs, policy/provenance identity,
and original source-row drill-down. The fixture identity is logical and stable across installation
paths. This is a bounded M7.1 showcase slice; Issue #60 remains open for anomaly lifecycle,
suppression/review, and broader procurement anomaly acceptance.
