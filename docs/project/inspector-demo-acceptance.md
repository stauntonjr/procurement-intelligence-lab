# Local inspector showcase

Date: 2026-09-18

Part of [Issue #50](https://github.com/stauntonjr/procurement-intelligence-lab/issues/50).
Related contracts: Issues #49 and #58, ADR-019, and the existing claim/source HTTP endpoints.
This slice does not complete those issues.

## Contract

The browser renders `/api/ask` values, statuses, evidence references, and recorded trace nodes.
Selecting an evidence reference sends its stable identifier and the form's explicit synthetic
tenant/project/site scope to `/api/source`. That endpoint retains authorization and fixture
lookup responsibility. The browser performs no quantity, cost, or reconciliation calculation.

The source view reads the admitted original synthetic workbook after verifying its content hash.
It renders the original XLSX headers and cell text for the selected row, highlighting only the
columns named by the EvidenceRef. Sheet, row, cells, source status, and evidence identity remain
inspectable. No PDF viewer, full spreadsheet editing, production authentication, correction
submission, or complete multi-document procurement state is claimed. Cost displays no invented
currency. Null values remain “Not established.”

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

The README GIF retains three actual full-page browser screenshots: initial question, calculated
answer, and selected source. Frames pause for 3/4/7 seconds; the canvas is padded to a common
size. It is an edited walkthrough, not a latency measurement. The PNG provides a static option.

## Verification record

- Before implementation, the same browser submission produced JSON and noninteractive stages;
  no source-row action existed. This reproduced the missing public flow.
- Real-browser GPU walkthrough: expected value, status, source identity, coordinates, and parsed
  fields passed.
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

Final checks: `make check` passed (236 tests, 90.37% coverage, coverage ratchet, types, lint and
architecture); `make package-smoke` built and installed `procurement_intelligence_lab-0.1.0`;
`make challenges` passed all eleven current-code oracles and rejected all eleven known-bad
mutations. HTTP checks required permission to bind localhost; the sandbox-blocked challenge
attempt was not counted as a product failure. An obsolete untracked `domain/__pycache__`
directory was moved to a temporary backup before architecture verification.

Independent review found no actionable correctness findings. Reviewed `web.py` SHA-256:
`38879c153c18a005820647d0d9a404656f03af5f8d6f1daa4ef311c71489ecd4`.
The semantic evidence artifact records the implementation commit separately. Python coverage does
not measure browser JavaScript; browser checks above are separate observed acceptance evidence.
