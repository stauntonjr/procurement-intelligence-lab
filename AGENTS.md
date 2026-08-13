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

Issues are executable specifications. Every change must preserve provenance, typed failure boundaries, and the evidence contract. Read this file, relevant skills, and ADRs before changing architecture.

