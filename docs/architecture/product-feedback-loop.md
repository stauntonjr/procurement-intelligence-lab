# Product Feedback and User-Story Loop

## Purpose

The chat experience is both an intelligence interface and a product-discovery channel. Users should be able to express unmet needs, incorrect answers, workflow friction, bugs, and suggestions without leaving the conversation. Feedback must preserve enough execution context to reproduce what the user saw while preventing raw operational or sensitive content from being copied directly into public engineering systems.

The design goal is a rapid, evidence-backed loop:

```text
user interaction
    |
    v
in-chat product signal
    |
    v
context capture + classification
    |
    v
triage / deduplication / clustering
    |
    v
approved backlog item
    |
    v
GitHub Project / Issue
    |
    v
human + development-agent implementation
    |
    v
CI / eval / review / release
    |
    v
close the loop with affected users
```

## Product signals are not backlog items

Preserve what the user actually said before converting it into a requirement. A `ProductSignal` is an immutable source record analogous to a source assertion in the knowledge pipeline: it records the user's statement and the context in which it occurred, but it is not automatically an engineering decision.

Candidate signal types:

- `UNMET_NEED` — "what I really need is..."
- `WRONG_RESULT` — answer or calculation appears incorrect
- `DATA_QUALITY` — source, extraction, mapping, resolution, or reconciliation is wrong
- `BUG` — application behavior is broken
- `UX_FRICTION` — workflow is unnecessarily difficult
- `FEATURE_REQUEST` — explicit request for capability
- `WORKFLOW_OPPORTUNITY` — recurring operational work that may be automatable

A signal may later support zero, one, or many product opportunities or issues.

## Context captured with a signal

The backend should attach machine-readable context rather than asking the user to reproduce it manually:

- user/role identifier subject to privacy policy
- tenant and project scope
- conversation and source-message identifiers
- answer and claim identifiers
- evidence references
- application trace identifier
- deterministic tool/query results used by the response
- retrieval diagnostics and selected evidence where relevant
- reconciliation / entity-resolution / prediction identifiers where relevant
- code commit/version
- domain/schema/config versions
- model, prompt, embedding, reranker, or resolver versions where relevant
- timestamp and deployment/environment

For a report such as "that total is wrong," this should make it possible to trace:

```text
feedback
  -> answer claim
  -> application execution trace
  -> deterministic calculation / query
  -> operational state
  -> reconciliation
  -> resolved assertions
  -> source evidence
  -> implementation/config versions
```

## User experience

Every material chat answer should offer lightweight contextual controls such as:

```text
Helpful  |  Not helpful  |  Report issue  |  Suggest improvement
```

The user should usually provide only the missing semantic information. The system already knows the answer, claims, evidence, trace, and project context.

Examples:

- "PO-1042 was cancelled yesterday, but this answer still counts it."
- "What I really need is an alert whenever a BOM revision invalidates an existing PO."
- "These two SKUs are not the same item."
- "I want to compare this vendor's current lead time with its historical performance."

If an unmet need is ambiguous, the application may ask a minimal clarifying question that materially changes the product requirement, such as whether the user wants an alert, dashboard view, or on-demand query.

## User-story extraction

An LLM may propose a normalized candidate story from a raw signal, but the raw signal remains authoritative. Structured candidates should be treated as derived product intelligence rather than replacing user language.

Example:

```text
Raw signal:
"What I really need is to get warned whenever a new BOM revision invalidates an existing PO."

Candidate story:
As a procurement manager,
I want to be alerted when a BOM revision invalidates or changes
requirements already covered by a purchase order,
so that I can correct procurement before it affects schedule.

Related capabilities:
- revision reconciliation
- PO coverage
- anomaly detection
- notifications
```

Suggested structured fields:

```text
UserStoryCandidate
- signal_ids
- actor / role
- problem_statement
- desired_outcome
- current_workaround
- frequency
- business_impact
- affected workflow
- related projects/entities
- proposed capability
- confidence / ambiguity notes
```

## Bugs and wrong answers

Wrong-answer reports need stronger reproducibility metadata than ordinary feature requests. A `WRONG_RESULT` signal should retain references to the precise claims and evidence chain so triage can classify the failure by layer:

```text
source artifact
  -> document structuring
  -> schema mapping
  -> normalization
  -> source assertion
  -> entity resolution
  -> reconciliation
  -> operational state
  -> deterministic query / retrieval
  -> agent synthesis
  -> presentation
```

This allows the review workflow to distinguish, for example, an OCR error from an entity-resolution false merge or a stale reconciliation result.

## Triage and promotion

Do not automatically create a public GitHub Issue from every signal.

The promotion pipeline should support:

1. privacy/sensitivity screening
2. deduplication
3. clustering of semantically related signals
4. severity and business-impact assessment
5. reproducibility check for bugs
6. human or policy approval
7. sanitization into a public-safe backlog item
8. creation/linking of a GitHub Issue or Project item

Operational identifiers, source text, document contents, user identities, and tenant data must not be copied into the public repository.

## Product opportunities and clustering

Repeated signals should be allowed to aggregate into a higher-order `ProductOpportunity` rather than generating duplicate feature requests.

Example:

```text
17 signals across 6 projects
        |
        v
ProductOpportunity:
"BOM revision impact analysis"
        |
        +-- procurement users
        +-- engineering users
        +-- recurring workflow
        +-- high business impact
```

Embeddings, lexical retrieval, or LLM classification may propose clusters. Models provide evidence; triage policy or human review decides whether signals should be grouped.

Suggested opportunity fields:

```text
ProductOpportunity
- supporting_signal_ids
- normalized problem
- affected roles
- affected workflows
- frequency
- project/tenant breadth (aggregated safely)
- estimated impact
- product owner / status
- linked GitHub work items
```

## Backend boundaries

Suggested application capabilities:

```text
FeedbackService
- record_signal(...)
- attach_context(...)
- classify_signal(...)
- request_clarification(...)

ProductDiscoveryService
- find_related_signals(...)
- propose_cluster(...)
- propose_user_story(...)
- promote_to_opportunity(...)

TriageService
- assess_privacy(...)
- assess_severity(...)
- deduplicate(...)
- approve_for_backlog(...)

BacklogAdapter
- create_or_link_github_issue(...)
- update_project_item(...)
```

These interfaces should remain independent of GitHub. GitHub is an engineering-work adapter, not the product-signal system of record.

## Suggested domain types

The exact schema is deferred, but the architecture should anticipate types similar to:

```text
ProductSignal
FeedbackContext
UserStoryCandidate
ProductOpportunity
TriageDecision
BacklogReference
```

Raw signals should be append-oriented. Derived classifications, clusters, and candidate stories should be versioned so that product-analysis behavior remains auditable.

## Development-agent boundary

Operational application agents may collect, classify, and summarize product signals through constrained application services. They must not create unsanitized public GitHub issues directly.

Development agents operate on approved GitHub Issues and Projects after triage. This preserves the existing agent taxonomy:

```text
application agents
    act THROUGH the product

        triage boundary

 development agents
    act ON the repository
```

## Evaluation

Feedback intelligence should eventually be evaluated independently of product feature correctness. Useful measures include:

- signal classification accuracy
- duplicate detection precision/recall
- cluster purity / false merge rate
- user-story preservation of original intent
- sensitive-data leakage rate (target: zero)
- bug reproducibility rate from captured context
- fraction of promoted issues linked back to supporting signals
- time from signal to triaged work item
- time from approved work item to validated release

Clustering should prefer leaving uncertain signals ungrouped over collapsing distinct user needs into one opportunity.

## Showcase behavior

The integrated demo should eventually show this loop alongside evidence drill-down:

1. user asks a procurement question
2. application returns a claim with evidence
3. user selects "This isn't what I need"
4. user enters an unmet need
5. system captures a raw `ProductSignal` plus safe execution context
6. system proposes a candidate user story
7. user can confirm or refine the interpretation
8. signal appears in a triage/product-discovery view
9. an approved, sanitized opportunity can be promoted to GitHub work

This demonstrates that the system does not merely answer questions: it learns which operational capabilities users actually need while preserving disciplined engineering governance.

## Architectural invariant

> User feedback is captured with reproducible execution context, preserved as raw product signals, and promoted into engineering work only through explicit triage, sanitization, and privacy controls.
