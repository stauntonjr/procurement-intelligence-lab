---
name: test-public-interface
description: Test a CLI, HTTP route, HTML form, inspector, or other public entry point after changing its inputs, authorization, resources, output, or downstream service contract. Use when helper tests could pass while the shipped caller fails.
---

# Test public interfaces

1. Identify the documented entry point and its default user path.
2. Exercise the real boundary: parse the shipped form, send the actual HTTP request, invoke the CLI as a subprocess, or call the installed artifact.
3. Do not replace the public path with manually constructed internal context in the acceptance test.
4. Cover success, malformed input, missing authorization, conflicting scope, unknown identifiers, and typed error mapping.
5. Assert semantic output and evidence linkage, not only status codes or HTML presence.
6. Put cross-layer tests under `tests/integration/`; keep helper behavior under `tests/unit/`.
7. Run `make integration` and any matching challenge manifest before reporting completion.
