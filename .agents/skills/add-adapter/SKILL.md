---
name: add-adapter
description: Add or change an external-system, storage, document, retrieval, or transport adapter behind a project-owned port. Use when capabilities, unsupported variants, mapping mechanics, lifecycle behavior, or failure translation can affect callers while core semantics must remain independent.
---

# Add adapter

Read `AGENTS.md`, the primary Issue, and relevant ADRs. Define the port and supported capability set before implementing mechanics. Reject unsupported enum variants, formats, scopes, and lifecycle states explicitly.

Add adapter contract tests under `tests/contract/` for:

- every supported and unsupported capability;
- empty, sparse, reordered, malformed, and conflicting inputs;
- source coordinates, evidence, scope, and typed failures;
- deterministic ordering and replay;
- runtime resources and clean packaging when applicable.

Wire only in the composition root. Do not let adapter order or representation define domain truth. Document operational failure modes and run `make contract` plus the relevant challenge.
