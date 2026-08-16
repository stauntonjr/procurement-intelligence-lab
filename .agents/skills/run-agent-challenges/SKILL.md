---
name: run-agent-challenges
description: Create, validate, replay, or score development-agent challenges derived from semantic defects. Use when adding a regression oracle, testing whether an agent prevents or detects a known mistake, or changing the challenge manifest and runner.
---

# Run agent challenges

## Inputs

Require the shipped defect, introducing commit, affected semantic surfaces, deterministic oracle,
and public-versus-held-out classification.

## Procedure

1. Create one `evals/development_agents/challenges/CNNN.json` manifest per defect.
2. Record the introducing commit, semantic oracle, exact argv, executable known-bad equivalent,
   intended failure signature, affected surfaces, and prevention mechanisms.
3. Require current code to pass and the isolated known-bad equivalent to fail for the intended
   semantic reason. A prose finding or unrelated failure is not challenge evidence.
4. Score agent prevention, pre-merge detection, and repair separately. Record model/configuration,
   revision, duration, and outcome outside committed golden expectations.
5. Run `make challenge-validate` and `make challenges`.

## Output and failure boundary

Emit structured public-oracle evidence without claiming an agent score. Keep held-out tests,
credentials, prompts, and transcripts in the protected private evaluator. Fail when a mutation
survives, produces the wrong failure, or a public oracle is represented as blind evaluation.
