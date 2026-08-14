# Agent development loop

`Issue → read AGENTS.md, relevant skills/, and ADRs → inspect → plan → implement → make check → eval → visualize → document → self-review → PR`.

For planning/status synchronization, use [architecture-plan-sync](../../skills/architecture-plan-sync/SKILL.md) as part of this loop.

Autonomy levels are Observe (read and report), Analyze (propose diagnosis), Propose (write a plan/patch for review), and Execute (authorized implementation with checks). Development agents modify code under review; operational agents act only through explicit, policy-checked tools and never inherit development authority.

