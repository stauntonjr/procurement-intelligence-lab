# Demo storytelling and evidence-focus design

Status: approved design, awaiting implementation planning.

Primary milestone: M9 Integrated Demo. Primary Issue: #74. Part of M5 evidence-first UX and
#72 release evaluation. This work stacks on PR #193 and does not authorize merge or deployment.

## Purpose

An interviewer or reviewer should understand the problem, the system boundary, and the value of
the live workflow before seeing the reviewer UI. The live demo should then make the exact evidence
supporting a finding visually obvious without changing procurement facts, governing policy, or
approval authority.

Success means a first-time viewer can answer these questions without repository context:

1. Who uses the system and what decision are they reviewing?
2. Why is an evidence-first workflow safer than a dashboard or unconstrained model answer?
3. How do source records become governed state, a review finding, and an auditable result?
4. Why does conflicting or missing evidence produce `not_assessed` instead of zero or completion?
5. Which source documents and cells support the currently displayed finding?

## Deliverables

### Native presentation

Create an editable presentation in the user's connected presentation workspace and retain a local
PDF/rendered-slide export for review and video composition. The deck uses a restrained evidence and
audit visual system: dark navy for structure, amber for conflict or unresolved evidence, and green
only for positively supported outcomes. Diagrams and narrative text remain native and editable.

The delivered sequence is:

1. **Procurement Intelligence Lab** — value proposition: from conflicting documents to a
   reviewable, evidence-backed decision.
2. **Who, What, Why, How** — procurement reviewers/project controls/buyers/auditors; reconciliation
   of expected requirements and observed records; preservation of missing, stale, superseded, and
   conflicting evidence; deterministic policy plus explicit human review.
3. **Architecture** — evidence plane to knowledge/state plane to decision/review plane. Show
   documents and feeds, structured assertions, identity/resolution, governed state, anomaly
   explanation, human review, and audit ledger. Model interpretation is visibly separate from
   deterministic facts and approval authority.
4. **Hypothetical Evidence Conflict** — approved BOM revision A says four GPUs; approved revision B
   says six; neither supersedes the other; an order observation says two. The requirement remains
   unresolved rather than becoming four, six, zero, or complete.
5. **Conflict Processing Flow** — capture both records, highlight source cells, retain competing
   assertions and times, apply governing-source policy, abstain on unresolved conflict, present a
   cited review finding, and record the human disposition without rewriting the evidence.
6. **Procurement Scenarios** — quantity mismatch, missing order observation, conflicting or
   superseded requirements, price deviation, late commitment, duplicate/conflicting order lines,
   stale evidence/incomplete coverage, and interrupted-review recovery.
7. **Other Applicable Verticals** — inventory/warehouse reconciliation, manufacturing quality,
   contract/regulatory compliance, insurance claims, financial close, clinical-trial/laboratory
   evidence review, infrastructure change control, and supply-chain traceability. Label every item
   as a potential application; procurement remains the only implemented vertical.
8. **Live Demo Transition** — invite the viewer to follow one conflict from original documents to a
   human-reviewed result and repeat the compact end-to-end flow.

Slide notes or compact citations identify the repository architecture and product contracts used
for claims. The deck must not imply production deployment, completed cross-domain portability,
model factual authority, automatic conflict resolution, or procurement side effects.

## Reviewer evidence-focus feature

Replace the undifferentiated evidence button list with an **Evidence used for this finding**
workspace while preserving existing source APIs and evidence identities.

- Every `facts.evidence` reference renders as a document card.
- The first evidence reference is loaded automatically after a valid finding renders.
- The selected card has a persistent visual and accessible selected state.
- Spreadsheet source responses display the existing highlighted cells plus explanatory text:
  “Highlighted cells support this finding.”
- Authority responses receive an explicit “Governing authority record” treatment and readable
  key fields; complete JSON remains available as detail rather than being the primary view.
- Selecting another card loads only that exact run-bound evidence reference.
- Empty evidence remains visibly empty and cannot imply support.
- Source loading failure preserves the current exact finding and selected-document identity while
  showing the existing safe error boundary.
- Busy, lock, replacement, recovery, and stale-callback behavior remain unchanged.

This is a public presentation-contract change, not a domain-semantic change. Authoritative inputs
remain the run-bound exact brief and its evidence references; authoritative outputs remain the
same source payloads. No document is classified as relevant unless it is already present in
`facts.evidence`. No model output supplies source authority, quantity, scope, approval, or save
permission.

User-facing review terminology changes with the same slice:

- “Exact persisted brief” becomes “Review finding”.
- “Approve exact brief” becomes “Approve this finding”.
- “Reject exact brief” becomes “Reject this finding”.
- “Exact brief SHA-256” becomes “Verified version”.
- Supporting copy says that approval applies only to this version and its cited evidence.

Internal type names, persisted schema, digests, and conflict checks do not change.

## Video composition

Produce a fresh browser recording rather than modifying the prior WebM. The presentation appears
first, followed by a direct transition into the live reviewer.

- Use a 1440 by 900 recording canvas with explicit top and bottom safe areas.
- Fit every slide and reviewer view without clipping meaning-bearing content.
- Use short reading pauses rather than the prior 40-to-80-second idle intervals.
- Target a concise combined runtime of approximately three to four minutes.
- Type visible questions, dates, and other scenario inputs character-by-character at a readable
  pace instead of filling an entire field atomically. Keep the caret and field in view, use a brief
  pause after the completed value, and then visibly submit the form so the viewer can follow the
  transition from human request to system processing.
- Add a persistent bottom banner during the live section. All banner text is italic and states the
  current scenario's **Who, What, Why, How, and When**.
- Update the banner when the scenario phase changes; do not obscure controls, evidence, source
  cells, status messages, or the trust-boundary explanation.
- Demonstrate one conflict case deeply. Additional mismatch and missing-observation outcomes may
  be summarized in the deck or shown briefly when runtime permits.
- Authentication occurs before publishable live frames or is visually masked. The private token is
  never shown or dynamically typed in publishable footage. Credentials must not appear in video,
  URL, storage, report, or logs.
- The video labels the run as local, synthetic, unmerged, and undeployed.

The browser interaction clock and final media-container duration are reported separately. Automated
pacing is not described as human rehearsal timing.

## Verification

Use test-driven changes at the shipped reviewer boundary.

- Unit/browser-page tests cover renamed copy, evidence-card construction, selected state,
  automatic first-source loading, authority rendering, empty evidence, lock clearing, malformed
  payload rejection, and failure preservation.
- Installed Chromium tests assert exact source linkage and highlighted cells through real HTTP.
- Existing credential erasure, storage/cookie, replacement failure, recovery, stale callback,
  approval, and idempotent-save assertions remain green.
- Run focused unit/integration tests, the real installed browser caller, package smoke, affected
  challenges, and `make check`.
- Validate the latest semantic-change evidence artifact even though the numerical procurement
  semantics remain unchanged, because the public evidence and review contract changes.
- Inspect every slide render and repair clipping, overflow, unreadable text, ambiguous arrows, and
  unsupported claims before recording.
- Verify the final WebM is seekable, has the intended dimensions, contains the complete slide/live
  sequence, visibly shows paced typing and submission of the scenario inputs, and has no credential
  text. Retain a compact report with scenario assertions and hashes.

## Non-goals and boundaries

- No new procurement calculation, precedence rule, anomaly kind, or source adapter.
- No automatic resolution of conflicting evidence.
- No new model authority, retry behavior, or model-quality claim.
- No purchase order creation or other external procurement action.
- No claim that hypothetical verticals are implemented.
- No merge, deployment, corpus expansion, or Issue closure in this slice.
- PR #193's independent coverage failure must be diagnosed separately; this work does not hide or
  overwrite that status.
