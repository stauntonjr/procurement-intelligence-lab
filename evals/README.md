# Evaluation manifests

Subdirectories hold versioned manifests and results for extraction, entity resolution, retrieval, application agents, development agents, and golden/system scenarios.

`development_agents/challenges/` contains C001-C008, the permanent semantic-defect challenge set. Run `make challenge-validate` to validate manifests and `make challenges` to execute their public deterministic oracles. Each manifest records the introducing commit, oracle, affected surfaces, and prevention mechanisms.

Public regression tests prevent recurrence but are not blind agent evaluations. Store held-out oracles and model-run credentials in a protected evaluator or private companion repository. Record model, configuration, revision, outcome, duration, and whether the agent prevented, detected, or repaired the defect; never commit hidden chain-of-thought.
