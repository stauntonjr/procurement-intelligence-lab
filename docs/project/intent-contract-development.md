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
model context. Generic prompt examples are not corpus entries. Each frozen run gets one attempt
per case; every failed candidate remains retained. This is an authored development exercise,
not independent/blind validation. No model/provider/budget swap or model reload.

| Configuration | Development targets | Failure disposition |
|---|---:|---|
| Original prompt, 998c35a | 17/20 | Three original Atlas abstentions reproduced; Borealis governance passed this repetition. |
| First clarification, bd5c376 | 18/20 | Original development misses passed, but inconsistent boundary and today wording incorrectly investigated. Rejected candidate. |
| Temporal checks first, e1637ea | 18/20 | All negative controls passed; original and independently authored consistent-boundary questions safely clarified. |

The final installed 48-case **development regression** passed **46/48**, with two unexpected
clarifications (`atlas-before-boundary`, `cinder-before-boundary`) and zero unknowns. Compared with
the original 41/48, five previously failed targets passed and all previously passing targets passed
this run. This is a paired observed development comparison, not broad or held-out accuracy.
Historical project accounting: Atlas11/12, Borealis12/12, Cinder11/12, Delta12/12. All twenty expected
abstentions passed. All twenty-six accepted investigations matched complete deterministic facts,
recovered in a second process, rejected an altered approval digest and repeated exact approval/save
with one result. Independent ledger reconciliation: 48 unique terminal inference attempts,
52 tool starts and 26 saved results. Deterministic HTTP:48/48 and464 original source checks.

The [compact retained outcomes](intent-development-results.json) include all three control runs,
postrun scored/journal reconciliation, immutable versions and the full regression outcomes/audit.
There were **108 actual inference attempts** in this experiment:60 controls plus48 regression.
The four original development probes occur in both the final controls and regression, so these
are not108 independent questions or one global attempt per question/configuration. Every frozen
run issued each case once, with no automatic retry; overlapping remeasurement is reported openly.

All three control runs have twenty unique terminal inference attempts each and zero saved results. A read-only
question containing injected approval/save commands may investigate, but still awaits exact human
review. Temperature zero did not reproduce the original Borealis miss; do not claim deterministic
inference. Raw prompt/response/hidden reasoning is not retained by the application journal.

Local artifacts (git-ignored): artifacts/intent-development/v1/baseline.json and candidate.json;
DBs /tmp/pil-intent-baseline.db and /tmp/pil-intent-candidate.db. The final full regression report is artifacts/intent-development/v1/regression.json and its DB is
/tmp/pil-intent-regression.db. No automatic retry or overwritten result.

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
full twenty-case denominator before failing the test. The current accepted candidate still fails
two positive development targets; the live opt-in test correctly exits nonzero. CLI acknowledged interpretation is not proof
of investigation; the test checks status, item, scope, exact cutoff and a live same-owned-run brief.
No approval command is issued by this test; the application ledger must contain zero saved results.

Final clean optional wheel: procurement_intelligence_lab-0.1.0-py3-none-any.whl, installed at
/tmp/pil-intent-env; versions checked before every run. The normal suite includes the transport,
strict model-output, permission, cross-run recovery and exact-save regressions. No shipped semantic
defect is introduced/fixed by this unmerged prompt experiment, so no new development-agent challenge
is claimed. C001-C017 remain applicable regression checks.

## Next work

Keep explicit ISO cutoff wording in the walkthrough, surface clarification honestly, and freeze a
fresh independently authored evaluation with protected train/development/held-out separation before
further tuning. Boundary-language reliability remains unresolved; avoid another prompt tweak based
on this same inspected evaluation. Preserve original tiny-fixture acceptance and actual browser/
accessibility/release tests as distinct subsequent slices. The corpus remains4projects/24workbooks/
960source-row occurrences; dataset expansion does not resolve interpretation failures.

The roadmap steward run37176028034 failed daily Gemini429 quota; no advisory report is claimed.
A deliberate live Project review found #53/#70/#72 In Progress and #71 Todo, with107items/25fields/
11views and zero configured missing fields/labels/milestones/views. No Issue closure or merge.

Full G2, actual browser/accessibility, deployment, original tiny-fixture routing, remaining release
adversarial checks and fresh held-out evaluation stay open. B2 corpus expansion remains gated.
