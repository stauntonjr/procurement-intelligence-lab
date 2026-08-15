---
name: implement-domain-logic
description: Implement or change domain calculations, reconciliation, governed state, status transitions, or policy semantics. Use for any change where scope, time, multiplicity, missing data, quantities, evidence, or failure rules can change a business answer.
---

# Implement domain logic

1. Read `AGENTS.md`, the primary Issue, linked ADRs, and existing tests.
2. Write the contract before code: authoritative inputs, authoritative output, scope key, as-of rule, deterministic policy, evidence retained, and typed failures.
3. Write a truth table covering applicable cases: empty, one, many, duplicates, conflicts, missing/unknown, stale/future, cross-scope, zero, negative, fractional, and boundary values.
4. Put intrinsic validity checks on immutable domain objects. Reject invalid construction instead of relying on one application path to sanitize it.
5. Require explicit policy for governing-claim selection. Never infer precedence from adapter order, collection order, or model output.
6. Add unit tests for local rules, contract tests for caller-visible semantics, and a regression test for every shipped defect. Use property-based tests when a value range defines the invariant.
7. Trace every material output to the exact evidence and decision that produced it. Absence of conflict is not positive evidence of success.
8. Run `make check` and the relevant C001-C008 challenges. Record the truth table and commands in the PR.
