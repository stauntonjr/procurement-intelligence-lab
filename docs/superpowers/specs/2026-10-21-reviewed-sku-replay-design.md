# Controlled reviewed source-SKU replay

Status: policy approved by the maintainer on 2026-10-21; implementation authorized; native plan in progress.
Issue: #222, M2, parent #41; ADR-042.
Baseline: main `a26d61510622121570a5eefbf8b056451601264b` / PR #221.

## Purpose and current boundary

Continue the core architecture with a useful controlled recomputation: produce a new source-local
SKU view from an immutable archived BOM and explicitly selected, approved source-value reviews.
The original source query remains reproducible and unchanged. This view does not establish
canonical identity, governing requirements, current operational state or procurement quantities.

Current correction impact already reports potentially stale registered references. Adding another
read-only stale flag would repeat that capability. The missing contract is what a reviewed replay
may consume, how it selects corrections, and how its new answer retains every material input.
This proposal is not executable functionality on main and does not complete #41 or M2.

## Alternatives and recommendation

1. **Explicit selected-review view (recommended).** A human selects an exact source and bounded
   approved review set. Execute deterministic row correction and set calculation, retain new
   references, and leave original results intact. No implicit precedence or current-state claim.
2. **Automatically use latest approvals.** Convenient but invents winner selection, conflict,
   supersession and governing-time policy. Existing review history deliberately selects no winner.
   Reject this option for this slice.
3. **Build a general invalidation/recompute executor first.** Broader orchestration and storage
   before one real correction-input contract. Defer general scheduling and producer adoption.

## Authoritative inputs and selection policy

- Exact StateScope/version and archived source snapshot, with the existing BOM assertion profile.
- Explicit selection of 1..32 distinct document-value review task IDs, each resolving to its exact
  retained task digest, APPROVE decision and accepted-correction identity at an inclusive as-of.
- Bounded caller-pinned local execution context and scoped request identity; trusted human recorder
  and server clock are injected. No client-supplied reviewer, approval or registration timestamp.
- Fixed policy `selected-reviewed-source-skus/v1`, with exact typed implementation metadata.

Each selected review must refer to a SKU assertion in that exact source snapshot. Resolve full
history through the review service and recheck domain admission. Pending, rejected, not-yet-visible,
foreign-source, foreign-scope and non-SKU reviews fail typed. Selecting two distinct tasks for the
same assertion fails, including equal proposals; do not pick one by list order, timestamp or ID.
Repeated task IDs fail input validation rather than silently changing the command.

Other approvals are not selected or silently applied. Output explicitly says
`correction_selection: explicit_selected_set` and `unselected_reviews: not_evaluated`. The result
is a selected reviewed view, not a claim that all corrections were incorporated or that it is
globally fresh. Determining a governing correction set remains outside this policy.

## Calculation and authoritative output

For each source SKU assertion, use its exact selected proposal if present, otherwise its original
value. Match by assertion identity, never by SKU token: correcting one of two GPU-A source rows
to GPU-B yields both GPU-A and GPU-B. Preserve case variants and exact source strings.

Produce a new immutable reviewed query reference with sorted/deduplicated known strings. Any
remaining or proposed null makes the complete value null/unresolved, with separately labeled known
values and exact missing row references. A review may resolve a missing source SKU, introduce a
missing value, or approve an equal value; equal values still create distinct reviewed provenance.
The existing source-query empty-source and 32-SKU-input limits remain explicit. No truncation.
Numeric-looking SKU strings remain strings; no quantities, prices or unit conversions are computed.

Return the reviewed value/status, original source/evidence, selected tasks/decisions/corrections,
actual row/query events and dependency receipt. Source assertions, original source-query values,
review history and governing state remain unchanged. No materialized query-result cache is added.

## Actual dependency and provenance contract

Approved proposed values are data inputs. They cannot be hidden in config hashes, parent-event
order or schema/model metadata merely to fit the current archive-only root contract.

Introduce a platform-neutral typed approved-correction root that pins the source assertion,
review task/digest, decision and correction identity. It resolves to the exact supported immutable
journal evidence and APPROVE outcome; a caller-supplied identity alone is not proof of admission.
Unsupported/missing review-evidence capability fails closed. Platform modules must not import
procurement; the composition root injects source/review admission and the domain producer.

For each selected row, actually execute a deterministic correction-application producer consuming
the original assertion and approved-correction root. It emits a distinct reviewed-row reference
with original/review evidence. Execute the final set producer over original unselected row references
and these reviewed-row outputs. Its at-most32 data inputs preserve the existing per-producer bound;
putting 32 original rows plus 32 corrections directly into one event would violate that bound.

At most32 source roots plus32 correction roots and33 producer references fit existing aggregate
128-root/256-reference budgets. Root ordering and identity must stay unambiguous across variants.
Actual events and the complete selection/as-of/context/result bind reference and command identity.
As-of must not disappear from retry identity just because the selected IDs happen to be unchanged.

Source-root correction impact remains conservative. A reviewed view must not be labeled globally
fresh merely because it incorporated the review currently being inspected. Global consumer coverage
stays `registered_graph_only` / `not_evaluated`; traversal completion is not global freshness.

## Time, authorization and retries

Require REVIEW plus READ_EVIDENCE and exact scope before storage I/O. Validate portable bounded
Unicode identities, exact container/enum types and fixed-offset times at boundaries and intrinsically
on immutable domain records. Validate context/clock before I/O, then sample registration time after
actual computation. Source recording and every selected approval precede the selected as-of;
as-of is no later than execution start, which is no later than server registration.

Exact source/selection/as-of/context/request/actor retries reproduce the reviewed view and return
the first registration receipt/time. Changed reused commands conflict atomically. A new explicit
selection is a separate execution, not an update to a previous result. No partial success if
registration fails; no operational-agent tool receives authority.

## Storage and compatibility requirements

Preserve old archive/review/dependency record shapes and readability. Additive typed root support
and any required dependency schema migration are explicit, versioned and separately admitted;
do not silently reinterpret archive-only schema1 or initialize/migrate during ordinary commands.
Archive1 and review1 data remain unchanged. The implementation plan must name the exact storage
version/capability transition after inspecting existing adapter constraints.

Both reads and appends must validate the retained source and review root binding. Malformed,
unapproved, corrupt or unavailable review evidence fails typed; it never becomes an empty root set.
Postgres mechanics remain behind ports. Generic registration remains a declaration, even when its
records happen to match the actual producer's shape; no production-attestation claim is introduced.

## Public caller and failure behavior

Use a separate explicit reviewed-replay CLI/service, not an implicit change to archived_bom_query
or approval behavior. The proposed caller is:

```bash
python -m procurement_intelligence_lab.interfaces.reviewed_bom_query \
  --scope scope.json --snapshot-id '<exact source snapshot>' \
  --reviews selected-reviews.json --as-of '2026-10-21T18:00:00+00:00' \
  --request-id 'reviewed-skus-1' --context query-context.json
```

`selected-reviews.json` is bounded32KiB strict UTF-8 JSON with exactly one field, `task_ids`, an
array of1..32 unique bounded IDs. Reject extra fields, duplicate keys and excessive nesting.
Context has the same three caller-pinned fields as the original query: run_id, code_revision and
started_at; fixed workflow/component/policy identities are server composed. Existing trusted local
reviewer/DSN conventions apply; manifest metadata remains caller-pinned, not attested. Read-only
source, journal and dependency commands remain separate from explicit capability initialization.

Malformed/unsupported input, scope denial, missing/future evidence, unapproved/conflicting selection,
request conflict, integrity failure and infrastructure unavailability retain distinct typed failures.
The actual CLI emits sanitized JSON/exit2 with no partial stdout or driver/credential leakage.

## Acceptance scenarios and delivery gates

| Family | Required evidence |
|---|---|
| Empty/missing/unknown | Empty selection/source fail; proposed null and unselected unknown retain unresolved/null; approved replacement can resolve a missing SKU |
| One/many/duplicate/conflict | One and32 selected rows; duplicate source tokens retain roots; duplicate task IDs and conflicting selected tasks fail; selection order is irrelevant |
| Scope/time | Exact source/version; pending/rejected/foreign/future decisions fail; inclusive approval/as-of boundary; malformed/future context rejected before I/O; no retroactive replay |
| Numeric/budgets | Numeric-looking strings unchanged; zero quantity arithmetic;32 SKU inputs accepted/33 rejected; intermediate row producers keep final inputs<=32 |
| Malformed/unsupported | Exact metadata/root types; invalid Unicode/context; missing correction-root capability; no implicit migration or unvalidated declaration upgrade |
| Public/artifact | Actual parser/subprocess and clean wheel/storage path, original file deleted, corrected result changes, retry/restart equal, original query and exported source bytes unchanged |
| Counterexamples | Correct one of duplicate SKU rows only; equal-value approval changes provenance, not claimed values; case variants distinct; unselected approvals never applied or labeled absent |

Also require golden old wire/read compatibility, atomic graph registration and changed-command
conflicts, real storage integrity/capability failure tests, exact-head full make check/coverage ratchet,
existing challenge compatibility and independent semantic/architecture review. New premerge capability
does not itself constitute a shipped defect; any discovered shipped defect follows AGENTS.md.

## Decision and handoff

The maintainer approved the explicit selected-review policy on 2026-10-21. ADR-042 is accepted
as a policy decision, not an implementation claim. The
[implementation plan](../plans/2026-10-21-reviewed-sku-replay.md) makes the root/store capability
transition, public caller, independent review and acceptance concrete; native execution follows the maintainer's approval to proceed.
Broader #13/#35/#37/#41/#46/#48/#56/#63, canonical/governing policy, scheduling, persistent result
materialization, production authentication/HA, operational tools, UI and deployment remain open.

The pre-slice stewardship run39657670491 on exact baseline failed Gemini503; deterministic Project
audit and manual source/contract review are separate evidence, not a successful advisory report.
