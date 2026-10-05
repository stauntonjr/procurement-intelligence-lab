# Procurement reconciliation review design

Status: approved design, awaiting implementation planning.

Primary milestone: M9 Integrated Demo. Primary Issue: #74. This work continues PR #193 and
requires a new ADR because it adds an authoritative reconciliation decision and changes the
review HTTP contract. It does not authorize merge, deployment, or procurement execution.

## Purpose

A procurement analyst should encounter the business discrepancy and its evidence before internal
workflow state. The analyst must understand exactly what can be confirmed, challenged, or resolved.
For an unresolved requirement conflict, the analyst may choose which revision governs the exact
item, project, and site under review, or deliberately keep that scope unresolved.

Success means that a first-time procurement analyst can:

1. request a discrepancy check without repository or implementation vocabulary;
2. understand the competing requirement values and observed procurement activity;
3. inspect the highlighted source evidence before deciding;
4. distinguish confirming an assessment from selecting a governing revision;
5. record a prospective, scoped reconciliation decision with a required rationale; and
6. understand that the decision does not rewrite history, discard source assertions, or trigger a
   purchase or other external action.

## Authoritative semantics

The authoritative inputs are the authenticated reviewer, exact tenant/project/site/item scope,
the investigation cutoff, the exact persisted assessment and digest, both eligible conflicting
revision assertions, their evidence references, and the analyst's explicit choice and rationale.

The allowed review outcomes are:

- `confirm_assessment`: confirm that the displayed discrepancy assessment is supported without
  changing reconciliation state;
- `select_governing_revision`: choose exactly one displayed eligible revision for the exact
  tenant/project/site/item scope;
- `keep_unresolved`: affirm that neither displayed revision should govern yet; and
- `assessment_needs_correction`: decline the displayed assessment without selecting a governing
  revision.

A governing-revision choice creates a durable reconciliation decision. It is effective at the
server-recorded save time and may affect only state evaluated at or after that time. The caller
cannot provide or backdate the effective time. Historical operational state, derived facts,
anomalies, saved reviews, and other decisions remain unchanged. Both winning and losing source
assertions and their evidence remain available. A later authorized reconciliation decision may
supersede the current decision prospectively.

The scope is the exact item + project + site under review. Selecting a revision does not establish
document-wide precedence and does not affect another item, project, site, or tenant. A non-empty
bounded rationale is required for `select_governing_revision` and `keep_unresolved`. The decision
records reviewer identity, recorded/effective time, scope, selected assertion when applicable,
all candidate assertions, rationale, policy/version identity, and evidence references.

After a governing selection, the application deterministically recomputes current operational
state and the discrepancy assessment for that exact scope. The expected quantity comes from the
selected source assertion; observed order evidence remains separate. Confirmation, unresolved,
and correction outcomes do not manufacture a governing value.

## Analyst-facing workflow

The primary page order is:

1. **Check procurement evidence**
2. **Discrepancy assessment**
3. **Source evidence**
4. **Resolve or review**
5. **Technical details and recovery**

The request form uses analyst language:

- fixture input: **Item to review**;
- live input: **Procurement question**;
- time input: **Evidence available through**;
- submit control: **Check for discrepancies**; and
- helper: “Compares governing requirements with recorded procurement activity using evidence
  available through this time.”

Remove interview, reference-demo, demo-brief, draft, typed-request, finding, owned-run, persisted-run,
and saved-result language from the primary workflow. Environment limitations may remain in a compact
non-primary development notice, but must not describe the analyst's task.

The assessment leads with a plain-language statement such as:

> Required quantity cannot be determined. Revision A requires 4 GPUs and revision B requires
> 6 GPUs. Neither currently supersedes the other. The order record contains 2 GPUs, so the
> requirement-versus-order comparison is not assessed.

The exact displayed wording is derived from typed facts, not model prose. Evidence cards and the
highlighted source viewer follow immediately. Internal identifiers, digests, raw JSON, application
events, prior investigations, and recovery controls move below the analyst decision in collapsed
technical sections. Recovery becomes prominent only when a selected prior investigation actually
requires recovery.

## Resolution controls

When the requirement is unresolved because two eligible revisions conflict, show these explicit
choices using revision labels and values from the exact assessment:

- **Use revision A — 4 each for this item**
- **Use revision B — 6 each for this item**
- **Keep this item unresolved**
- **Assessment needs correction**

The page explains the effect before submission. Selecting A or B establishes that assertion as the
governing requirement prospectively for this item/project/site only. Keeping unresolved records an
explicit reviewed reconciliation decision without choosing a value. Marking the assessment as
needing correction does not alter governed state.

The analyst must enter a rationale before saving a governing or unresolved reconciliation choice.
The final action label reflects the selected operation, for example **Save revision B as governing**
or **Save unresolved decision**. No generic Approve/Reject buttons remain. The UI shows the scope,
effective-now rule, and “no historical changes” statement adjacent to the action.

For non-conflict assessments, the page offers only semantically applicable controls. It must not
offer revision precedence when there are not exactly two eligible conflicting revision assertions.

## Application and storage boundaries

Add a domain reconciliation-decision type and repository-owned port before changing the browser.
The HTTP request identifies only the exact run/assessment/digest, the closed outcome, an eligible
assertion ID when required, and the rationale. Identity, scope, candidate assertions, effective
time, and authorization remain server-owned.

The application atomically validates that:

- the assessment is still active and digest-exact;
- the reviewer is authorized for the scope;
- the selected assertion is one of the displayed eligible candidates;
- all candidates and evidence still match the assessment;
- the request outcome and selected assertion are structurally compatible;
- the rationale is present where required; and
- no newer reconciliation decision already governs that exact scope.

On success, persist the immutable reconciliation decision, project a new operational-state version
effective at the same server timestamp, and recompute the scoped derived assessment. A replay of the
same exact request returns the same decision identity. A conflicting replay, stale assessment,
foreign assertion, cross-scope reference, changed evidence, or later governing decision fails with
a typed conflict and performs no partial write.

The existing review receipt may continue to record confirmation/correction outcomes, but it cannot
stand in for a reconciliation decision. The implementation plan must decide whether to extend the
current store transaction or introduce a composed unit-of-work port; the domain records remain
framework-independent either way.

## Failure and scenario behavior

- Empty or missing candidates cannot be resolved.
- One eligible requirement is already governed and does not show precedence controls.
- More than two conflicting candidates remains unresolved in this slice; do not truncate the set
  or offer a misleading A/B choice.
- Duplicate assertion identities fail validation.
- Equal-valued eligible assertions use the existing shared-value policy, not human precedence.
- Missing observations remain unknown; selecting a requirement does not turn absence into zero.
- Zero, negative, and fractional values retain existing quantity policy.
- Future assertions remain ineligible at the investigation cutoff.
- The effective time is server-generated and prospective; caller-supplied or retroactive time is
  rejected.
- Cross-tenant, cross-project, cross-site, and cross-item candidates are rejected.
- Source or persistence failure leaves the existing assessment and operational state unchanged.
- No resolution triggers a purchase, message, alert, or other external action.

## Verification

Use test-driven implementation and record the semantic-change evidence contract.

- Domain tests cover all closed outcomes, prospective time, exact scope, candidate membership,
  retained losing evidence, required rationale, replay identity, stale/conflicting decisions, and
  historical-state preservation.
- HTTP integration tests cover authentication, malformed requests, foreign assertions, stale
  digests, cross-scope inputs, server-owned effective time, atomic failure, and exact response.
- Browser tests cover analyst-first ordering, plain-language assessment, evidence before controls,
  dynamic revision labels, rationale gating, explicit action labels, post-resolution recomputation,
  keyboard/focus behavior, and collapsed technical history.
- A real installed-browser scenario selects one revision, proves only the exact item/project/site
  current state changes, proves an earlier as-of result is unchanged, and verifies both source
  assertions remain inspectable.
- Add a development-agent challenge for any shipped semantic defect found during implementation.
- Run focused tests, `make integration`, `make check`, package smoke, affected challenges, and the
  latest-revision independent semantic review before re-recording the demo.

## Durable documentation

Implementation requires a new ADR for prospective human reconciliation overrides, updates to the
local browser/live-review contracts, semantic-change evidence, handoff and milestone status, and a
revised demo script and recording. PR #193 must distinguish implemented behavior from the approved
design until the code and public-caller evidence exist.

## Non-goals

- Document-wide supersession.
- Retroactive or caller-selected effective dates.
- Bulk reconciliation across items or projects.
- Editing, deleting, or silently replacing source assertions.
- Automatic model selection of a governing revision.
- Prediction, policy decision, procurement execution, or external actions.
- Production identity, deployment, or Issue #74 closure.
