---
name: test-public-interface
description: Test a CLI, HTTP route, HTML form, inspector, or other public entry point after changing its inputs, authorization, resources, output, or downstream service contract. Use when helper tests could pass while the shipped caller fails.
---

# Test public interfaces

## Inputs

Require the documented entry point, default user path, public contract, authorization/scope rules,
and changed revision.

## Procedure

1. Exercise the real boundary: parse the shipped form, send the actual HTTP request, invoke the CLI
   as a subprocess, or call the installed artifact.
2. Do not replace the public path with manually constructed internal context in acceptance evidence.
3. Cover success, malformed input, missing authorization, conflicting scope, unknown identifiers,
   and typed error mapping as applicable.
4. Assert semantic output and evidence linkage, not only status codes, imports, or HTML presence.
5. Put cross-layer tests under `tests/integration/`; keep helper behavior under `tests/unit/`.
6. Run `make integration`, clean-package smoke when applicable, and matching challenges.

## Output and failure boundary

Record the exact public command/request, revision, and semantic assertions in the change evidence.
Do not report completion when only helper construction was tested, the real boundary was skipped, or
sandbox restrictions were misreported as product behavior.
