---
applyTo: "src/procurement_intelligence_lab/**/agents/**/*.py,src/procurement_intelligence_lab/**/actions/**/*.py,src/procurement_intelligence_lab/interfaces/mcp/**/*.py"
---

# Operational-agent review rules

- Agent-framework state is execution state, never canonical procurement/business state.
- Agent tools should expose semantic application capabilities rather than arbitrary SQL, Cypher, shell, or unrestricted code execution.
- Reads and writes must be distinguishable; consequential writes require explicit authorization and approval policy.
- Verify tenant/project scope on every relevant operation and do not rely on the model to remember access filters.
- Side effects must be idempotent where retries are possible and must emit auditable records.
- Treat tool/model inputs as untrusted. Check prompt/tool injection boundaries and avoid passing retrieved text into privileged instructions without controls.
- LLMs may interpret, plan, and synthesize; deterministic code/policy should own arithmetic, permissions, state transitions, thresholds, and irreversible effects.
- Material claims returned to users need typed evidence references and epistemic status.
