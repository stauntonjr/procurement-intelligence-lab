# Dependabot update policy

Dependabot is the repository's bounded intake for routine Python/uv, GitHub
Actions, and the lockfile-pinned roadmap-review CLI. The authoritative configuration is
[`.github/dependabot.yml`](../../.github/dependabot.yml).

## Review and merge contract

- Dependabot pull requests run the same deterministic PR checks as every other
  pull request: PR-contract validation, static/architecture checks, tests,
  dependency review, and any applicable package or challenge checks.
- AI review is advisory. No workflow polls for an AI review or makes review
  arrival a merge invariant. This keeps a bot-authored update from waiting on a
  quota-limited or unavailable reviewer.
- A human maintainer must inspect the dependency diff and approve the pull
  request. No auto-merge is enabled by this policy.
- Action version pinning and immutable-reference enforcement are a separate
  hardening slice tracked by Issue #121; this file does not silently expand
  that scope.
- Action updates are constrained by the immutable-reference and allowlist
  policy in [the Actions supply-chain policy](github-actions-supply-chain.md).
- npm updates are limited to `.github/roadmap-steward`, where the exact Gemini
  CLI dependency and its transitive integrity hashes are retained in `package-lock.json`.

## Triage and rollback

1. Confirm the update is within the expected ecosystem, group, and weekly
   cadence. Check the lockfile diff and release notes for breaking changes.
2. Wait for the deterministic checks, then inspect failures as an ordinary
   change. A failing update is closed or revised; it is not merged because a
   bot check is green.
3. If a merged update regresses behavior, revert the dependency-only commit or
   PR, rerun `make check`, and open a follow-up issue with the failing package,
   versions, and reproduction. Do not disable Dependabot globally to recover.
4. Adjust grouping, cooldown, or limits only through a reviewed change to the
   configuration and its executable contract test.

Ownership is the repository maintainer's responsibility; Dependabot proposes
changes, while deterministic CI and human review decide whether they enter the
main branch.
