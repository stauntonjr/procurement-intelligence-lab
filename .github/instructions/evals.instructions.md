---
applyTo: "evals/**/*,docs/evaluation/**/*,src/procurement_intelligence_lab/evaluation/**/*.py,tests/regression/**/*"
---

# Evaluation review rules

- A quality-improvement claim must identify the baseline, candidate configuration, dataset/version, metrics, and reproducible run context.
- Separate candidate-generation recall from pair-scoring/decision quality in entity-resolution evaluation.
- Report false merges explicitly; prefer unresolved identity over an unjustified merge.
- Separate document-structuring metrics from schema-mapping/extraction metrics so failures can be localized.
- Retrieval changes should report task-appropriate ranking/relevance metrics and inspect error cases, not only aggregate scores.
- LLM/prompt/program changes require task-success or correctness metrics; subjective prompt readability is not evidence of improvement.
- Preserve run metadata such as git SHA, schema/config/model/prompt versions, dataset version, and seed when meaningful.
- Do not silently tune on the held-out evaluation set.
