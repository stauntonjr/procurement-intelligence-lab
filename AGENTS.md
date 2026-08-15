# Repository Constitution

- Core owns semantics; adapters own mechanics.
- Models produce evidence; policies produce decisions.
- Keep the domain framework-independent. Use explicit dependency injection and a visible composition root.
- Use stdlib `dataclasses` for domain objects; use Pydantic only at system boundaries.
- Prefer `Protocol` over inheritance. Put intrinsic, strongly coupled behavior on dataclasses.
- Prefer deterministic code paths. Put external technologies behind ports and adapters.
- Architecture changes require an ADR. Model or algorithm swaps require benchmark evidence.
- Never add confidential or proprietary data.
- Development agents and operational agents are distinct and must not share authority implicitly.

## Shared project memory

Repository artifacts are the canonical shared engineering memory across ChatGPT, Work, Codex, humans, and other development agents. Conversational history is exploratory, transient, and non-authoritative.

A fresh agent must read `AGENTS.md`, [`docs/project/handoff.md`](docs/project/handoff.md), the relevant GitHub Issue, and linked ADRs/docs before making changes. Material architectural or product decisions discovered in chats must be written back to durable repository artifacts. PRs that materially change project state should update the handoff index when appropriate.

Chat/Work is for exploration and planning. Codex and other development agents implement against the repository. GitHub docs, Issues, ADRs, and PRs are the durable shared state; do not persist hidden chain-of-thought or entire chat transcripts.

Issues are executable specifications. Every change must preserve provenance, typed failure boundaries, and the evidence contract. Read this file, relevant skills, and ADRs before changing architecture.

## Semantic change contract

Before changing a business calculation, adapter, public interface, or runtime package:

1. Name the authoritative inputs and output; scope and as-of key; governing policy; evidence retained; and typed failure behavior.
2. Read every Issue governing semantics touched by the change, including later-milestone work. Do not invent future policy inside an earlier delivery slice.
3. Cover applicable empty, one, many, duplicate, conflict, missing, stale, future, cross-scope, zero, negative, fractional, and boundary cases.
4. Test the real public caller. Manually constructed helper context is not acceptance evidence for a browser, HTTP, CLI, or installed-package path.
5. Validate a clean built artifact whenever package metadata, entry points, examples, or runtime resources change.
6. Treat unknown, absent, and unresolved as distinct from zero, complete, or reconciled. Success requires positive evidence.
7. Add a regression oracle and development-agent challenge manifest for every shipped semantic defect.

Use `skills/implement-domain-logic/SKILL.md`, `skills/add-adapter/SKILL.md`, `skills/test-public-interface/SKILL.md`, `skills/release-smoke/SKILL.md`, and `skills/run-agent-challenges/SKILL.md` as applicable.

## GitHub planning administration

Use `skills/manage-github-planning/SKILL.md` as the authoritative procedure for creating, updating,
and verifying Issues, native parent-child relationships, labels, milestones, Project fields and item
values, and saved Project views. `.github/planning.json` is the repository-owned expected-state
contract; live GitHub remains the operational tracker.

Authenticate through the keyring-backed `gh` session, inspect before every write, and audit after
every batch. Retry a network-blocked `gh` operation through the environment's approved network
mechanism rather than misreporting a sandbox failure as a GitHub capability limitation. Never expose
the token or delete planning objects without explicit authorization.


## Primary delivery loop

For every non-trivial repository slice, use the `skills/architecture-plan-sync/SKILL.md` procedure as part of the normal agent loop:

1. **Orient:** read the handoff, milestone map, relevant Issue, ADRs, and architecture documents. Before a major new slice or after a merge wave, run the read-only [roadmap stewardship audit](docs/development/roadmap-stewardship.md) and review the current GitHub Project deliberately.
2. **Implement:** keep the smallest vertical slice, its acceptance evidence, and durable decision record aligned. Record material Chat/Work conclusions in an Issue, ADR, or project document.
3. **Close out:** after merge, update the linked Issue status when its acceptance criteria are complete; update the handoff, milestone map, README/roadmap, and Project fields when their state materially changed. Use `Closes #<issue>` only for a fully completed Issue; otherwise say `Part of #<issue>`.
4. **Report:** distinguish `main` from planned work and report confirmed planning drift explicitly.

The roadmap steward is advisory and read-only. It cannot access Chat/Work history or update repository/GitHub state; agents and maintainers deliberately materialize durable corrections through normal PRs and Issue/Project updates.

Do not merge while required deterministic checks are pending or failing. Automated review remains advisory, but its review must arrive and every actionable thread must be resolved or explicitly rebutted before merge.
