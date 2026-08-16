---
name: semantic-change-loop
description: Specify, implement, verify, and close out changes to business calculations, policy, governed state, adapters that alter meaning, public contracts, or runtime/package behavior. Use for implementation work where scope, time, multiplicity, missing data, values, evidence, failures, or a public answer can change. Do not use for wording-only docs, formatting, or behavior-preserving private refactors.
---

# Semantic change loop

## Inputs

Require a linked Issue, relevant ADRs/docs, changed semantic surfaces, and the current revision. Read
`AGENTS.md`, `docs/project/handoff.md`, and applicable focused skills before editing.

## Loop

1. **Orient.** Trace the real caller to authoritative inputs and policy. Read later-milestone Issues
   that govern touched semantics; do not invent policy from the current implementation.
2. **Specify.** Create the contract defined by
   `docs/development/semantic-change-evidence.schema.json`. Cover every scenario family. Mark a
   family not applicable only with a concrete rationale.
3. **Make the gap executable.** Add a failing example, property, metamorphic relation, contract
   test, or public-boundary test before relying on implementation changes.
4. **Implement narrowly.** Use `.agents/skills/implement-domain-logic/SKILL.md`,
   `.agents/skills/add-adapter/SKILL.md`, or `.agents/skills/test-public-interface/SKILL.md` as applicable. Preserve
   evidence and typed failures.
5. **Verify.** Run focused tests, the real public caller or clean artifact when applicable,
   `make check`, and affected challenges. Record exact argv and outcomes.
6. **Review the latest revision.** Use `.agents/skills/review-semantic-change/SKILL.md` in a fresh pass.
   Resolve or record every finding, then rerun invalidated checks.
7. **Close out.** Validate the evidence with `tools/validate_semantic_change.py`. Update durable
   docs and planning state, and claim completion only for the recorded revision.

## Required output

Produce a JSON evidence artifact matching the canonical schema, plus a PR body that identifies the
same contract, scenarios, commands, and reviewed revision. Record observable evidence only; never
store hidden reasoning or private evaluator content.

## Stop conditions

Do not report ready when policy is missing, a scenario lacks evidence or rationale, a required real
caller was replaced by helper construction, a command failed or was skipped, review targets an older
revision, or findings remain unresolved.
