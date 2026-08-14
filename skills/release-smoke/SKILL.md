---
name: release-smoke
description: Validate Python packaging, package data, clean installation, and advertised runtime commands. Use whenever pyproject metadata, entry points, runtime resources, examples, release workflows, or CLI defaults change.
---

# Release smoke test

1. Build artifacts into a temporary directory.
2. Inspect wheel contents for every runtime resource.
3. Create a clean virtual environment outside the checkout and install the wheel without repository-path leakage.
4. Run every advertised minimal command from that environment and validate semantic output.
5. Treat source-checkout tests as insufficient packaging evidence.
6. Run `make package-smoke`; include the wheel name and result in the PR evidence.
