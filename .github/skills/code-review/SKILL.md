---
name: code-review
description: Review pull requests for correctness, architecture invariants, provenance, security boundaries, and repository acceptance criteria. Use for PR code review.
---

# Pull request code review

1. Read `AGENTS.md`, the PR description, changed files, and relevant ADRs.
2. Determine the semantic surface changed: domain, application, port, adapter, interface, persistence, intelligence/eval, or operational agent.
3. Verify dependency direction and explicit DI/composition-root conventions. Flag infrastructure/framework construction inside domain/application services.
4. Verify the semantic pipeline remains explicit: structure -> mapping -> normalization -> source assertions -> entity resolution -> canonicalized assertions -> reconciliation -> operational state -> derived intelligence.
5. Check provenance. Material user-facing claims should retain machine-readable evidence paths to source evidence and implementation versions.
6. Check probabilistic/deterministic boundaries. Models may produce evidence or proposals; deterministic policies should own authoritative calculations, permissions, state transitions, and consequential decisions where practical.
7. Inspect failure handling: retryable, non-retryable, and human-review outcomes must not be conflated.
8. Check tests/evals against the PR's acceptance criteria. If the PR claims intelligence-quality improvement, use the evaluation-review skill criteria.
9. Check security and sensitive-data handling, especially for public-repository fixtures and agent/tool changes.
10. Report only actionable findings. Distinguish blocking correctness/security/invariant findings from optional design suggestions. Avoid duplicating formatter/linter output.
