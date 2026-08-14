# ADR-011: Evidence inspector is a read-only client of deterministic claims

Status: accepted

## Context

The public showcase needs a chat interface and evidence inspector that can drill from a material answer to exact source locations. The M1 pipeline already produces deterministic query results, reconciliation outcomes, and framework-independent evidence nodes.

## Decision

Expose read-only, typed claim results and evidence chains from the application layer. The evidence inspector consumes those results and may render source locations, statuses, conflicts, and unresolved decisions. A chat adapter may select and explain these tools, but it must not bypass their deterministic query, reconciliation, or provenance paths.

## Alternatives

Allow the UI or an LLM to assemble claims directly from source records. This was rejected because it would make provenance and abstention behavior inconsistent.

## Consequences

The first runnable demo is JSON rather than a web UI, so the same contract can later serve a CLI, HTTP adapter, and inspector without moving semantic rules into presentation code.

## Evidence and follow-up

Add a read-only inspector adapter that renders claim-level drill-down. Introduce stable assertion, mention, decision, and claim identifiers before persistence or multi-document review.
