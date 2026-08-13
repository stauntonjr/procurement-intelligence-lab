# Agent development loop

`Issue → read AGENTS/skills/ADRs → inspect → plan → implement → make check → eval → visualize → document → self-review → PR`.

Autonomy levels are Observe (read and report), Analyze (propose diagnosis), Propose (write a plan/patch for review), and Execute (authorized implementation with checks). Development agents modify code under review; operational agents act only through explicit, policy-checked tools and never inherit development authority.

