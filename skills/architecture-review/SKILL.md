# Architecture review

Read `AGENTS.md`, the primary Issue, linked ADRs, the PR contract matrix, and changed tests. Trace the change against dependency direction, authoritative state, scope/as-of rules, evidence lineage, typed failures, public callers, packaging, and roadmap status.

Apply the domain scenario matrix when calculations or policy change. Apply `skills/add-adapter/SKILL.md` for adapters, `skills/test-public-interface/SKILL.md` for public faces, and `skills/release-smoke/SKILL.md` for distributable behavior. Require benchmark evidence for model or algorithm swaps. Report violated contracts with a triggering input and consequence; identify unresolved hypotheses explicitly.
