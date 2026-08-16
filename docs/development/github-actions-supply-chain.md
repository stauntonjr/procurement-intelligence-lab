# GitHub Actions supply-chain policy

Every third-party Action in `.github/workflows/` must use a reviewed full
40-character commit SHA and a readable version comment. The checked-in
allowlist at [`../../.github/actions-allowlist.json`](../../.github/actions-allowlist.json)
is the repository's exported policy of permitted Action repositories and their
trust rationale.

`make check-fast` runs
`tools/check_actions_supply_chain.py`. It fails when a workflow introduces an
unallowlisted Action, a mutable tag/branch, a short SHA, or a missing version
comment. Dependabot may propose SHA revisions, but a human reviews the release
and the resulting diff.

A top-level SHA does not make a composite Action immutable when its
`action.yml` invokes other Actions by mutable tag. Explicitly approved
third-party composite Actions are prohibited unless every transitive `uses:`
reference is both allowlisted and pinned to a full SHA. Prefer a
repository-owned wrapper with an ecosystem lockfile when an upstream composite
does not meet that boundary.

## Repository setting

The repository Actions setting should be configured to allow only actions
created by GitHub, verified creators, and the repositories listed in the
allowlist. The JSON file is deliberately checked in because GitHub's setting
is remote configuration and must be audited alongside the workflow references;
it is not treated as a substitute for that setting.

Verify the live setting with `gh api` against
`repos/stauntonjr/procurement-intelligence-lab/actions/permissions` and its
`selected-actions` subresource. The expected top-level values are
`allowed_actions: selected` and `sha_pinning_required: true`; explicit public
repository patterns must not exceed the repositories justified by the
checked-in allowlist.

## Rollback

If a pinned revision breaks a workflow, restore the previous reviewed SHA in a
small pull request, run the affected workflow trigger and `make check`, and
record the reason in the PR. Do not revert to a mutable version tag as an
emergency workaround. If the action is no longer needed, remove it from the
workflow and allowlist together.
