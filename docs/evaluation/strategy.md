# Evaluation strategy

Use unit, contract, integration, regression, golden, system, application-agent, and development-agent evaluations. Measure each layer: extraction field accuracy and localization; mapping coverage; normalization validity; assertion provenance completeness; ER precision/recall with false merges weighted more heavily than unresolved identities; reconciliation correctness; retrieval grounding; calculation correctness; agent tool policy and evidence coverage.

Every evaluation uses a versioned manifest naming dataset, schema, code/model versions, prompt versions, thresholds, environment, and expected tolerances. Results are reproducible and stored as artifacts. Synthetic fixtures precede any public-data expansion.

