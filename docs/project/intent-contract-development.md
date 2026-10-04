# Intent contract development — 2026-10-04

Primary #53; Part of #72/#70. Continuation of G2 on the unmerged draft stack.

## Contract and experiment

Read-only requirement governance/conflict and document approval applicability belong to the review
intent. A document-relative predicate uses the selected aware cutoff; it does not grant human
approval authority. Calendar-boundary wording must agree with that cutoff. Different explicit dates,
inconsistent boundaries and unresolved relative query times still require clarification. Core
quantity/governance policy, literal-item guard, proposal validation and exact human approval remain
unchanged. See [ADR032](../adr/032-local-model-intent-and-journal.md).

The first [48-case pilot](g2-pilot-evaluation.md) is immutable: 41/48, seven unexpected abstentions.
All its queries have now been inspected and are development regression cases. Historical split
labels are retained for denominators only. New reports explicitly say development_regression.
No old case can be presented as fresh held-out evidence after this tuning. A fresh independently
authored frozen evaluation remains required before a quality claim or corpus expansion.

The [20-case development manifest](../../evals/operational_agents/intent-development-v1.json) was
frozen at 998c35a before prompt changes: four original Atlas/Borealis development misses and sixteen
new controls, including contradictory cutoffs, aliases, multiple items, foreign scope, actions and
injected approval/save instructions. No control labels, case IDs, quantities or source gold enter
model context. Generic prompt examples are not corpus entries. Each configuration gets one attempt
per question; every failed candidate remains retained. This is an authored development exercise,
not independent/blind validation. No model/provider/budget swap or model reload.

| Configuration | Development targets | Failure disposition |
|---|---:|---|
| Original prompt, 998c35a | 17/20 | Three original Atlas abstentions reproduced; Borealis governance passed this repetition. |
| First clarification, bd5c376 | 18/20 | Original development misses passed, but inconsistent boundary and today wording incorrectly investigated. Rejected candidate. |

Both runs have twenty unique terminal inference attempts and zero saved results. A read-only
question containing injected approval/save commands may investigate, but still awaits exact human
review. Temperature zero did not reproduce the original Borealis miss; do not claim deterministic
inference. Raw prompt/response/hidden reasoning is not retained by the application journal.

Local artifacts (git-ignored): artifacts/intent-development/v1/baseline.json and candidate.json;
DBs /tmp/pil-intent-baseline.db and /tmp/pil-intent-candidate.db. Durable compact outcomes follow
when the bounded experiment concludes. No automatic retry or overwritten result.

## Reproduction

Build a clean wheel and install it outside the checkout with frozen optional workflow dependencies.
The opt-in test verifies installed immutable versions before asking any question:

```bash
PIL_INTENT_PYTHON=/tmp/pil-intent-env/bin/python \
PIL_INTENT_DATABASE=/tmp/pil-intent-FRESH.db \
PIL_INTENT_OUTPUT=artifacts/intent-development/v1/FRESH.json \
.venv/bin/python -m pytest -q tests/integration/test_live_intent_development.py
```

The normal test suite skips this opt-in test and performs no inference. Failed targets retain the
full twenty-case denominator before failing the test. CLI acknowledged interpretation is not proof
of investigation; the test checks status, item, scope, exact cutoff and a live same-owned-run brief.
No approval command is issued by this test; the application ledger must contain zero saved results.

Full G2, actual browser/accessibility, deployment, original tiny-fixture routing, remaining release
adversarial checks and fresh held-out evaluation stay open. B2 corpus expansion remains gated.
