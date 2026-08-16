---
name: implement-domain-logic
description: Implement or change domain calculations, reconciliation, governed state, status transitions, or policy semantics. Use for any change where scope, time, multiplicity, missing data, quantities, evidence, or failure rules can change a business answer.
---

# Implement domain logic

## Inputs and contract

Require the linked Issue, relevant ADRs, existing tests/callers, and the behavioral contract from
`.agents/skills/semantic-change-loop/SKILL.md`. The contract must name authoritative inputs/output, scope,
as-of behavior, deterministic policy, evidence, and typed failures before code changes.

## Procedure

1. Cover every applicable scenario family in the contract, including explicit not-applicable
   rationale. Do not reduce missing, unknown, or unresolved to zero or success.
2. Put intrinsic validity checks on immutable domain objects. Reject invalid construction instead of
   relying on one application path to sanitize it.
3. Require explicit policy for governing-claim selection. Never infer precedence from adapter,
   collection, or model order.
4. Add unit tests for local rules, contract tests for caller-visible semantics, and a regression test
   for every shipped defect. Use property or metamorphic tests when ranges or transformations define
   the invariant.
5. Trace every material output to the exact evidence and decision that produced it. Absence of
   conflict is not positive evidence of success.
6. Run focused tests, `make check`, and affected challenges. Record exact argv and outcomes.

## Output and failure boundary

Return implementation, executable tests, and updated semantic-change evidence. Stop without a
completion claim if policy is ambiguous, applicable cases lack evidence, required provenance is
lost, failures are untyped, or validation does not pass on the recorded revision.
