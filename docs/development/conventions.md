# Development conventions

Use Python 3.12, `uv`, Ruff, Pyright (strict, because it gives fast boundary feedback without runtime coupling), and pytest. Use Google-style docstrings. Import direction is domain → application → ports; adapters/interfaces may depend inward, never the reverse. Use snake_case modules, PascalCase types, and typed domain errors with stable error codes. Structured logs must support OTel/Logfire hooks without making either mandatory. Secrets come from environment/secret managers, never files committed to Git.

Use opaque typed IDs, decimal money with currency, and explicit units/quantities. Classify failures as input, interpretation, identity, policy, infrastructure, transient, or authorization. Feature flags are explicit and audited. Prompts and model configurations are versioned artifacts. Generated code is disposable and never the source of semantic truth. Done means checks pass, evaluation evidence exists where relevant, docs/ADR impact is handled, and the evidence chain is preserved.

