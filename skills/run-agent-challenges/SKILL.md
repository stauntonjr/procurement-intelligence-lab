---
name: run-agent-challenges
description: Create, validate, replay, or score development-agent challenges derived from semantic defects. Use when adding a regression oracle, testing whether an agent prevents or detects a known mistake, or changing the challenge manifest and runner.
---

# Run agent challenges

1. Create one `evals/development_agents/challenges/CNNN.json` manifest per defect.
2. Record the introducing commit, semantic oracle, exact argv command, affected surfaces, and prevention mechanisms.
3. Keep the oracle executable and deterministic. A prose finding without a failing test is not a challenge.
4. Verify prevention, pre-merge detection, and repair separately. Record model/configuration and run metadata outside committed golden expectations.
5. Run `make challenge-validate` for structure and `make challenges` for current-code oracles.
6. For a blind evaluation, keep held-out tests in a protected evaluator or private companion repository. Public regression tests prevent recurrence but do not measure unaided discovery.
