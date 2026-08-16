# ADR-021: Enforce semantic quality with layered tests and agent challenges

Status: accepted

## Context

Several deterministic defects survived green unit tests because fixtures mirrored implementation assumptions, public callers and built artifacts were not exercised, domain policy was implicit, and advisory review sometimes arrived after merge. Local delivery-slice labels also reused GitHub milestone identifiers with different meanings.

## Decision

Use GitHub's M0-M9 milestones as the only milestone taxonomy. Historical implementation sequence labels use S0-S9.

Enforce known contracts with required static, unit, contract, integration, regression, package-smoke, and challenge-manifest checks. Put shipped semantic defects into C001-C008 manifests with deterministic oracles. Keep AI review advisory: do not require it to arrive, consume a model API credential, or make merge eligibility wait.

Public regression tests measure recurrence prevention. Truly blind development-agent evaluation uses the private companion repository [`stauntonjr/procurement-intelligence-lab-evaluator`](https://github.com/stauntonjr/procurement-intelligence-lab-evaluator) because a public repository cannot hide its oracle. Its aggregate output follows the public [baseline report schema](../../evals/development_agents/baseline.schema.json); held-out oracles, credentials, and transcripts remain private.

## Consequences

Changes take longer to merge but provide executable evidence at the boundary where a defect can occur. Coverage is a ratchet, not a substitute for semantic scenarios. The checked-in [coverage baseline](../../.github/coverage-baseline.json) records the evidence-backed line and branch rates; CI rejects either rate falling below that baseline. GitHub Issues, milestone state, Project fields, and repository status documents must be reconciled deliberately.
