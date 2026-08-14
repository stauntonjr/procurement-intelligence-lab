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


## Primary delivery loop

For every non-trivial repository slice, use the `.agents/skills/architecture-plan-sync/SKILL.md` procedure as part of the normal agent loop:

1. **Orient:** read the handoff, milestone map, relevant Issue, ADRs, and architecture documents. Before a major new slice or after a merge wave, run the read-only [roadmap stewardship audit](docs/development/roadmap-stewardship.md) and review the current GitHub Project deliberately.
2. **Implement:** keep the smallest vertical slice, its acceptance evidence, and durable decision record aligned. Record material Chat/Work conclusions in an Issue, ADR, or project document.
3. **Close out:** after merge, update the linked Issue status when its acceptance criteria are complete; update the handoff, milestone map, README/roadmap, and Project fields when their state materially changed. Use `Closes #<issue>` only for a fully completed Issue; otherwise say `Part of #<issue>`.
4. **Report:** distinguish `main` from planned work and report confirmed planning drift explicitly.

The roadmap steward is advisory and read-only. It cannot access Chat/Work history or update repository/GitHub state; agents and maintainers deliberately materialize durable corrections through normal PRs and Issue/Project updates.
