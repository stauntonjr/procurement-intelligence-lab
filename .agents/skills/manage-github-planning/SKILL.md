---
name: manage-github-planning
description: Audit and administer this repository's GitHub Issues, parent-child relationships, labels, milestones, Projects v2 metadata, fields, item values, and saved views. Use when an agent must create, update, reconcile, or verify GitHub planning state from Codex or a terminal.
---

# Manage GitHub planning

Use authenticated `gh` as the durable control plane. The GitHub connector is useful for ordinary
Issue reads and writes, but it does not replace `gh project` or GraphQL Project administration.
Treat `.github/planning.json` as the expected operating-model contract and live GitHub as the
operational tracker.

## Required sequence

1. Read `AGENTS.md`, `docs/development/github-plan.md`, and the relevant Issue.
2. Run `python tools/github_planning.py preflight`.
3. Run `python tools/github_planning.py audit` and inspect live state before writing.
4. Resolve names to numeric or node IDs from live output. Never copy IDs from another Project.
5. Apply the smallest requested mutation with `gh`; avoid interactive prompts.
6. Re-read the changed object and the complete Project item set. Use `--limit 500`.
7. Report exact URLs, IDs, counts, and residual drift. Do not claim success from command exit alone.

If a managed environment blocks network access, retry the same `gh` command with the environment's
network/escalation mechanism. A sandbox denial is not evidence that GitHub lacks the capability.

## Authentication boundary

- Verify identity with `gh auth status` and `gh api user --jq .login`.
- Require `repo` for repository Issues/labels/milestones and `project` for user Projects.
- Use the keyring-backed token. Never print, copy, commit, or embed it.
- Stop if the authenticated login or repository differs from `.github/planning.json`.

## Operations

### Issues and hierarchy

Use `gh issue create` and `gh issue edit`. Prefer `--body-file` for substantial Markdown. Attach
native hierarchy with `gh issue edit NUMBER --parent PARENT`. Verify the resulting Issue body,
milestone, labels, state, parent, and Project membership.

### Labels

Use `gh label create NAME --color COLOR --description DESCRIPTION` and `gh label edit NAME`.
Before deleting or renaming, list dependent Issues and obtain explicit authorization because those
operations can remove planning information.

### Milestones

Use the versioned REST endpoint through `gh api`:

```text
gh api --method POST repos/OWNER/REPO/milestones \
  -H 'X-GitHub-Api-Version: 2026-03-10' \
  -f title='M10 Example' -f description='Outcome'
```

Use `PATCH repos/OWNER/REPO/milestones/NUMBER` for updates. Query with
`gh api --paginate --slurp 'repos/OWNER/REPO/milestones?state=all&per_page=100'` and verify by
milestone number, not list position.

### Project, fields, membership, and item values

Use `gh project edit`, `field-create`, `field-delete`, `item-add`, `item-archive`, and `item-edit`.
Fetch the Project node ID, item IDs, field IDs, and single-select option IDs immediately before a
write. `item-edit` changes one field per invocation; repeat it deliberately for multi-field updates.

After bulk changes, run:

```text
gh project field-list 6 --owner stauntonjr --format json
gh project item-list 6 --owner stauntonjr --limit 500 --format json
```

### Saved views

GitHub's live GraphQL schema supports `createProjectV2View`, `updateProjectV2View`, and
`deleteProjectV2View`. Reconcile the non-destructive desired set with:

```text
python tools/github_planning.py sync-views
python tools/github_planning.py sync-views --apply
python tools/github_planning.py audit
```

The first command is a dry run; `--apply` creates missing views and updates matching named views.
Unmanaged views are preserved. To remove one, first remove it from `.github/planning.json`, then run
`python tools/github_planning.py delete-view --name 'Exact name'` as a dry run. Use `--apply` only
when the user explicitly authorizes that named deletion; the tool verifies the remaining views.

## Safety and completion

- Inspect before create so retries do not duplicate Issues, milestones, fields, items, or views.
- Never delete Projects, fields, items, labels, milestones, or views as an inferred cleanup step.
- Preserve unrelated Project items and custom fields.
- Do not close an Issue until all acceptance criteria are complete on `main`.
- If an API changes, inspect `gh help` and the live GraphQL schema before declaring a limitation.
- A complete result includes a post-write audit with zero missing configured fields, labels,
  milestones, and views.
