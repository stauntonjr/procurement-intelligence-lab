# LangChain Academy reference for the procurement demo

Studied 2026-10-03. These are source-grounded engineering notes and original small examples,
not an adoption ADR or a claim that the courses or production integration were completed.

## Access and provenance

Both supplied `/courses/take/` lesson-player URLs redirected to sign-in. Public curricula and
the official companion repositories were accessible. Videos, private lesson text and course
transcripts were not reviewed. Relevant Python scripts/notebook cells were inspected without
executing upstream agents, making model calls, or uploading traces.

| Course | Public course page | Official materials inspected |
|---|---|---|
| Building Reliable Agents | [Curriculum](https://academy.langchain.com/courses/building-reliable-agents) | [lca-reliable-agents at 8fe1c139](https://github.com/langchain-ai/lca-reliable-agents/tree/8fe1c139767fa6efc32e9b21230cff8f45932356/python); Python README explicitly identifies this course |
| Introduction to LangGraph | [Curriculum](https://academy.langchain.com/courses/intro-to-langgraph) | [langchain-academy at fa15bec4](https://github.com/langchain-ai/langchain-academy/tree/fa15bec4a51c541c40c261586b037c9d134977b1); introduction, state, interruption, parallelism and memory examples |

Repository HEADs were resolved during this study, not assumed from an older local checkout.
[sources.json](sources.json) records pins, selected file hashes, inspection depth, and current-doc
URLs. Upstream READMEs, requirements and APIs can disagree over time; pin the actual optional
runtime dependencies and verify behavior before copying an example into application code.
Both source repositories carry the MIT license; [upstream-license.txt](upstream-license.txt)
preserves their common notice. Notes/examples here are project-specific adaptations, not vendored
notebooks. No course datasets, databases, generated traces or credentials are added to this repo.

## Read in this order

1. [Reliable-agent lessons](reliable-agents.md): experiments, evaluation, trace pitfalls.
2. [LangGraph lessons](langgraph-patterns.md): channels, joins, interrupts and persistence.
3. [Adapted snippets](snippets.md): small graph sketches and an executable offline evaluator.
4. [Application checklist](procurement-application.md): exact Issues and acceptance checks.

## Recommended reuse

| Adopt as a pattern | Adapt to this project | Defer |
|---|---|---|
| Small, explicitly typed tool boundaries | RequestContext stays server-owned; tools call existing services | Arbitrary SQL tools |
| Checkpointed review workflow | Approval binds exact brief and evidence snapshot; save is idempotent | Long-term learned procurement memory |
| Code-based trajectory evaluation | Require successful applicable tool outcomes; missing trace is unknown | LLM judge as authority over quantities/policy |
| Dataset + target + evaluator experiments | Gold stays outside runtime; fixed versions and project splits | Prompt optimization before baseline |
| Optional nested tracing | Application audit remains authoritative; redact before export | Synthetic traces presented as measured runs |

This supports #53/#66/#67/#68/#70/#72/#75 and the
[corpus implementation plan](../superpowers/plans/2026-10-03-procurement-demo-corpus.md).
The historical [framework evaluation](../architecture/agent-framework-evaluation.md) remains
useful for architecture boundaries; its older deferral language predates the current Issue-led
demo direction. These notes do not make LangGraph or LangSmith a core dependency.

## Validation boundary

`python3 docs/langchain-ref/examples/trajectory_gate.py` exercises the original stdlib example
against passing and adversarial records. Graph snippets are syntax-checked reference sketches;
they have not been imported or executed against a pinned LangGraph environment. No restart,
live-inference, telemetry-export, or procurement-quality claim follows from these checks.
