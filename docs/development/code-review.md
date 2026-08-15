# Pull request review governance

## Principle

Use deterministic systems to enforce known invariants and AI reviewers to surface judgment-heavy risks. Do not make merge safety depend on an LLM reviewer agreeing with a change.

## Review layers

### Required or candidate-for-required deterministic checks

- `CI / checks`: Ruff formatting/lint, Pyright, pytest, documentation-presence checks, and deterministic architecture import checks.
- `CodeQL (Python)`: semantic security scanning using GitHub CodeQL with the `security-extended` query suite.
- `Dependency Review`: reject newly introduced dependencies with known `high` or `critical` vulnerabilities. Dependency additions still require architectural justification even when vulnerability-free.

Repository branch/ruleset settings should make deterministic checks required only after they have demonstrated a low false-positive rate. Security findings should be evaluated at the finding level; do not weaken checks merely to obtain a green build.

### Advisory AI review

GitHub Copilot code review is the default general AI reviewer. It is guided by:

- `AGENTS.md` for cross-agent repository rules;
- `.github/copilot-instructions.md` for always-on review priorities;
- `.github/instructions/*.instructions.md` for path-specific rules;
- `.github/skills/code-review/` for architecture/provenance review procedure;
- `.github/skills/evaluation-review/` for ML/LLM/intelligence quality claims.

AI review is advisory. High-confidence findings should be resolved or explicitly rebutted, but neither Copilot approval nor review arrival is a merge invariant. Reviewers may be requested by a maintainer when their judgment is useful; required status checks remain deterministic.

## Review responsibilities

### General code review

Focus on correctness, maintainability, typed failure behavior, dependency direction, and whether the implementation satisfies the Issue/PR acceptance criteria. Avoid duplicating formatter/linter output.

### Domain-logic reviewer

For changes to domain calculations, reconciliation, state transitions, or policy logic, reviewers use [the domain-logic review procedure](../../.github/skills/domain-logic-review/SKILL.md). It applies a concrete scenario matrix—scope, time/as-of, duplicates, partial/stale/unknown inputs, quantity boundaries, and conflicting evidence—to find semantic defects and turn them into executable tests. This is a focused responsibility for Copilot or an explicitly requested specialist reviewer, not an additional merge gate or generic bot.

### Architecture Guardian

Architecture is partly deterministic and partly judgment-based.

Deterministic checks currently enforce that the framework-independent `domain/` package imports only standard-library or project-owned modules. Additional rules should migrate into deterministic checks only when they can be expressed with low ambiguity.

AI review additionally checks semantic leakage such as infrastructure objects defining domain concepts, models directly deciding canonical state, or an adapter-specific representation escaping its boundary.

### Evaluation Reviewer

PRs claiming extraction, entity-resolution, retrieval, reranking, prompt/model, forecasting, or agent-quality improvements must include reproducible evidence against a baseline. See `.github/skills/evaluation-review/SKILL.md` and `docs/evaluation/`.

### Security and agent safety

CodeQL covers code-level vulnerability classes. Operational-agent code additionally requires review of authorization, tenant/project scope, tool privilege, prompt/tool-injection boundaries, approval policy, idempotency, and auditability. These are path-specific Copilot review concerns until deterministic policy checks become practical.

### Provenance review

As the evidence architecture matures, material user-facing claims must remain traceable through machine-readable evidence references to deterministic computations/state, reconciliation and resolution decisions, source assertions, structured source elements, and original artifacts. Provenance review should become increasingly machine-enforceable over time.

## Automatic Copilot review setting

Repository administrators may enable automatic GitHub Copilot code review for pull requests and re-review on new pushes. This is a repository setting rather than a workflow file. Keep its judgment advisory: do not require an AI review to arrive on a particular commit, and do not make merge eligibility wait for it.

The PR workflow policy test locks this boundary: pull-request-triggered workflows must be deterministic and must not expose model API credentials, invoke Gemini, or poll for an AI review. Fork pull requests therefore follow the same secret-free deterministic checks as same-repository PRs.

## Runner security

All PR review workflows run on GitHub-hosted runners. Future trusted self-hosted/GPU runners must not execute arbitrary code from untrusted public pull requests. Expensive or trusted-machine evaluations should be triggered only through reviewed/authorized paths.

## Adding another reviewer

Do not add another generic AI review bot merely for coverage. A new reviewer must have a distinct responsibility, measurable benefit, and low overlap with existing checks. Prefer enhancing repository-specific Copilot instructions/skills or adding deterministic checks before adding another bot.
