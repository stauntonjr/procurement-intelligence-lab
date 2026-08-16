---
name: review-semantic-change
description: Review a proposed semantic or public-contract change against its Issue, behavioral contract, scenario evidence, and latest revision. Use for fresh-pass review of business calculations, reconciliation, policy, governed state, evidence semantics, adapters that change meaning, public callers, or completion claims. Do not use as a formatter/linter pass or to repeat an author's rationale.
---

# Review a semantic change

## Inputs

Require the linked Issue, applicable ADRs, changed files, behavioral-contract evidence, and exact
revision under review. Read source and tests directly; do not rely on the author's summary as proof.

## Review procedure

1. Reconstruct authoritative inputs, output, scope/as-of rule, governing policy, retained evidence,
   and typed failures from durable sources.
2. Compare that contract with the evidence artifact. Flag omitted or unjustified scenario families.
3. For each applicable family, ask for a concrete counterexample that would make the implementation
   wrong. Inspect empty/unknown, multiplicity/conflict, scope/time, numeric boundaries,
   unsupported/malformed, public-artifact, and safe-counterexample behavior.
4. Confirm cited tests exercise the changed branch and assert semantics rather than implementation
   shape. Inspect mutation, property, metamorphic, public-caller, or package evidence when relevant.
5. Verify commands and review evidence belong to the exact latest revision. A green workflow with
   no revision-bound review artifact is not evidence that review occurred.
6. Check restraint: do not invent findings for valid exceptions, unrelated changes, or explicitly
   inapplicable scenarios with sound rationale.

## Output

For each finding, report the violated contract, triggering input, observable consequence, file or
surface, and safe corrective direction. Separate blocking correctness findings from optional design
suggestions. If there are no findings, state the reviewed revision and scenario families inspected.

Do not approve completion while required evidence is missing, stale, skipped, or contradicted by the
implementation. Do not expose hidden challenge oracles or save private reasoning transcripts.
