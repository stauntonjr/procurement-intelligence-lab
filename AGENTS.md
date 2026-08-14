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
