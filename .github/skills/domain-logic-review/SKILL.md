---
name: domain-logic-review
description: Review domain calculations, reconciliation, state transitions, and policy logic for semantic correctness and missed edge cases.
---

# Domain-logic review

Use this procedure when a pull request changes domain calculations, reconciliation, state transitions, authoritative policy, or their tests.

## Establish the contract

1. Read `AGENTS.md`, the linked Issue, relevant ADRs, and the changed tests before judging the implementation.
2. State the authoritative inputs, outputs, scope key, time/as-of rule, evidence requirements, and whether the result is deterministic.
3. Reject implementations that silently infer missing business semantics from adapter order, model output, or incidental collection order.

## Exercise the scenario matrix

Check the changed behavior against the cases that apply:

- **Scope:** tenant, project, site, revision, authorization boundary, and records with the same business key in different scopes.
- **Time:** as-of cutoff, latest eligible observation, future records, correction/replay ordering, and timezone/date boundary where relevant.
- **Multiplicity:** duplicate inputs, competing observations, ties, idempotent replay, and deterministic selection or aggregation.
- **Completeness:** empty inputs, missing evidence, partial, stale, delayed, substituted, and unknown state; do not silently turn unknown into zero or complete.
- **Values:** zero, negative, fractional, overflow/precision, required-versus-received bounds, and invalid combinations that need typed rejection.
- **Evidence:** retained provenance for every material derived claim and an explainable path from input to result.
- **Failure/action boundary:** typed failure or human review when the contract cannot be satisfied; no anomaly, prediction, or action implied by a state comparison alone.

## Require executable evidence

1. Require focused tests for every material scenario that changes the answer, especially the failure mode the implementation is most likely to hide.
2. Prefer table-driven examples, property/metamorphic tests, or a compact scenario matrix when the rule has several dimensions.
3. For an algorithm/model change, also apply `.github/skills/evaluation-review/SKILL.md`; a unit-test happy path is not sufficient quality evidence.
4. Report only concrete findings: violated contract, triggering input, observed consequence, and corrective direction.
