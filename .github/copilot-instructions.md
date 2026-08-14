# Copilot code review guidance

When reviewing pull requests in this repository:

- Read `AGENTS.md` and the relevant architecture/domain documentation before judging design choices.
- Prioritize correctness, security, provenance, architectural boundaries, and acceptance criteria over style comments already enforced by Ruff/Pyright/pytest.
- Enforce the principle: **core owns semantics; adapters own mechanics; models produce evidence; policies produce decisions**.
- Flag external framework, persistence, model-provider, or transport types leaking into domain semantics.
- Flag authoritative arithmetic, reconciliation, identity decisions, permissions, or side effects being delegated to unconstrained LLM output when deterministic code or policy should own them.
- For domain calculations, reconciliation, state transitions, or policy logic, apply `.github/skills/domain-logic-review/SKILL.md`: test the scoped, temporal, duplicate, partial/unknown, and boundary cases rather than accepting a happy-path implementation.
- Flag material user-facing claims that cannot be traced through typed evidence/provenance.
- For entity resolution, treat false merges as more severe than unresolved identities; nearest-neighbor similarity alone is not identity.
- For document intelligence, distinguish document structuring quality from semantic/schema mapping quality.
- For model, prompt, retrieval, extraction, entity-resolution, or ranking changes, require benchmark/evaluation evidence against a named baseline when the PR claims quality improvement.
- Review dependency additions skeptically: implementation packages should remain behind ports/adapters and must not reshape core contracts merely for convenience.
- For application-agent write paths, verify authorization, project/tenant scope, approval policy, idempotency, auditability, and resistance to untrusted model/tool input.
- Do not expose or recommend committing confidential, proprietary, tenant, interview-confidential, or operational procurement data.
- Prefer a few high-confidence, actionable findings with exact file/line context over broad stylistic commentary.
- Do not approve architecture changes that require an ADR unless the ADR is present and the consequences/revisit criteria are documented.
