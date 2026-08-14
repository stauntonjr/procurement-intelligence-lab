# ADR-019: Explicit request scope at query boundaries

Status: accepted

## Context

Evidence, operational-state, retrieval, review, and future action paths must not infer tenant, project, or site from an unscoped request. The synthetic prototype does not provide production authentication, but it still needs a testable boundary that prevents accidental cross-scope reads as adapters expand.

## Decision

Introduce an immutable `RequestContext` with principal, tenant, project, site, permissions, and trace identity. Application and port boundaries receive the context explicitly and require the relevant permission. Retrieval projections retain the scope that built them and reject a search context whose tenant/project/site does not match before ranking.

The local inspector accepts only its fixed synthetic fixture scope. Missing or conflicting scope returns a typed authorization failure; this demonstrates boundary behavior but is not a production identity provider or isolation guarantee.

## Consequences

Future adapters must resolve authentication and authorization into `RequestContext` before calling query or action services. Scope stays outside the semantic domain records until a governed multi-scope data model is introduced. Documents remain untrusted data and never grant scope or permission.
