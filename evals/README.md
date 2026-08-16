# Evaluation manifests

Subdirectories hold versioned manifests and results for extraction, entity resolution, retrieval, application agents, development agents, and golden/system scenarios.

`development_agents/challenges/` contains C001-C009, the permanent semantic-defect challenge set. Run `make challenge-validate` to validate manifests and `make challenges` to execute each public deterministic oracle twice: once against current code, which must pass, and once in an isolated checkout with its declared known-bad mutation, which must fail. Each manifest records the introducing commit, oracle, executable mutation, affected surfaces, and prevention mechanisms. The runner emits revision/configuration/duration/outcome metadata with `--results`; generated results are local artifacts.

Public regression and mutation tests prove that the oracle distinguishes current behavior from a known-bad equivalent. They are not blind agent evaluations. Store held-out oracles and model-run credentials in a protected evaluator or private companion repository. Record model, configuration, revision, outcome, duration, and whether the agent prevented, detected, or repaired the defect; never commit hidden chain-of-thought.
