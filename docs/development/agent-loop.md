# Agent development loop

`Issue → orient → specify behavior → make the gap executable → implement → verify the real boundary → review the latest revision → record evidence → PR`.

For a semantic change, use [semantic-change-loop](../../.agents/skills/semantic-change-loop/SKILL.md) and
record evidence using [the canonical schema](semantic-change-evidence.schema.json). Every scenario
family must have executable evidence or a concrete not-applicable rationale. A test command, model
review, or completion statement applies only to the revision it records. Embed the completed JSON
record under `## Semantic evidence JSON` in the pull-request body; the PR Contract check validates
that durable record against the actual head revision and the human-readable contract fields.

Use [review-semantic-change](../../.agents/skills/review-semantic-change/SKILL.md) for a fresh review pass.
Review reconstructs the contract from the Issue and source, searches for counterexamples, checks a
safe/unrelated case for restraint, and verifies the actual caller or artifact where applicable. It
records findings and unresolved findings, not hidden reasoning.

Run `make semantic-preflight` when these instructions, skills, routing fixtures, schema, validator,
or PR contract change. Public challenge mutations prove regression-oracle sensitivity; protected
agent runs separately measure prevention, pre-merge detection, and repair.

After a bounded harness experiment, publish its measured result and return to the product roadmap.
Do not continue into prompt optimization, framework adoption, or new evaluation infrastructure
without a separately tracked benchmark question and exit criterion.

For planning/status synchronization, use [architecture-plan-sync](../../.agents/skills/architecture-plan-sync/SKILL.md) as part of this loop.

Autonomy levels are Observe (read and report), Analyze (propose diagnosis), Propose (write a plan/patch for review), and Execute (authorized implementation with checks). Development agents modify code under review; operational agents act only through explicit, policy-checked tools and never inherit development authority.
