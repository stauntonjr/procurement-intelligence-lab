# Frozen G2 pilot evaluation

Primary M9/#72; part of #53/#70/#71. Branch `codex/g2-pilot-evaluation`, stacked on draft PR #181.
This evaluates branch work, not main or a deployed release. Runtime/application and prompt bytes
are unchanged from PR #181. No dataset expansion, model reload, provider provisioning or trace export.

## Frozen inputs and boundaries

[Execution plan](../superpowers/plans/2026-10-03-g2-pilot-evaluation.md) implements the approved
corpus plan's evaluator increment. `evals/operational_agents/g2-pilot-v1.json` freezes the hash of
all 48 original query texts and evaluator-only interpretation expectations before inference.
Projects: Atlas/Borealis development (24), Cinder validation (12), Delta test (12). Existing
structured gold remains a separate oracle; its item/action fields are never submitted to Qwen.
The caller submits only question, project and explicit as-of date.

Under ADR-032, 28 cases target investigation, 16 clarification and four unsupported actions.
The 12 identifier-free paraphrases target clarification, not factual answers chosen by gold.
A clarification pass measures the safe contract; it does not establish paraphrase retrieval quality.
Queries are publicly available, share schema/generator ancestry and correlated scenario templates.
This is a public synthetic development-held-out project split, not blind or contamination-proof
quality evidence. No prompt/model/expectation tuning occurred after this run. Earlier development
failures and prompt changes remain documented in [Qwen execution evidence](local-qwen-review-evidence.md).

## Executed results

Frozen first execution at evaluator commit `cdcc23b65f2ca7e26e5e7cfc967b65d54c302871`:

- Installed deterministic HTTP: 48/48 gold cases passed; all 464 returned original quantity and
  authority source references were checked through the public source route against source labels.
- Live interpretation and applicable end-to-end checks: 41 pass, seven fail, zero unknown;
  development 20/24, validation 11/12, test 10/12.
- All 21 accepted investigations matched complete deterministic facts, recovered through a new
  CLI process, rejected altered approval, and completed repeated exact approval/save with one result.
  Their recorded successful-tool/terminal trajectories passed. All 20 expected abstentions passed.
- Seven unexpected abstentions: Atlas conflict/future-approval unsupported and before-boundary
  clarified; Borealis conflict unsupported; Cinder before-boundary clarified; Delta approved-boundary
  and future-approval clarified. These are failed product-target interpretations, not wrong factual
  answers. None ran tools or saved a result. No retries or tuned rerun erase these failures.
- Independent post-run ledger audit binds the original question hash/date and owned/versioned run
  for every case: 48 unique actual terminal inference attempts, 42 tool starts and 21 saved results.
  No fixture/replay attempts enter these counts. Pending attempts would have unknown model-call count.
- Model transport elapsed: 0.722–1.169 seconds, median 0.836. Public multi-process round trips and
  event trajectory elapsed are retained separately; model timing is not total user-perceived latency.

Compact [results and run identities](g2-pilot-results.json) are checked in. Full retained bundles:
`artifacts/g2-pilot/v1/first-run.json` and `independent-attempt-audit.json`. The original bundle
remains untouched; the later audit adds independent causal/count evidence without recalling Qwen.
The audit path is included automatically in subsequent fresh runner executions.

Command:

```sh
.venv/bin/python -m tools.run_g2_pilot --run-live \
  --python /tmp/pil-qwen-acceptance-env/bin/python \
  --database /tmp/pil-g2-pilot-v1.db \
  --output artifacts/g2-pilot/v1/first-run.json
```

Use fresh database/output paths. The runner rejects overwriting a prior evaluation and verifies
that clean-wheel application/model/prompt/tool/corpus/framework versions match the checkout before
inference. Golden-source HTTP validation runs first; a failed baseline blocks live execution.
Individual timeout/partial outcomes are retained; omitted cases summarize as unknown. The runner
requires `--run-live`; interpreter selection preserves the supplied virtual-environment symlink.
The installed handler is launched on an OS-selected loopback port; no product route is replaced.

## Acceptance and next work

The bounded pilot is **not ready: seven failed interpretations**. Prioritize a development-only
intent contract/prompt investigation of governing-requirement and approval/time wording, with
explicit caller-date semantics. This run is immutable; a future model/prompt revision needs a new
frozen evaluation and must not relabel inspected validation/test cases as untouched held-out data.
Do not broaden to fuzzy aliases, retrieval or expansion to hide these failures.

Actual browser tools again returned no enabled apps/browsers. Browser/accessibility, deployed
walkthrough, original tiny-fixture live routing and remaining G2 adversarial/release gates stay open.
No general accuracy, model superiority, full G2 completion or corpus-expansion acceptance is claimed.
The advisory [roadmap audit](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/37172143348)
failed with Gemini daily-quota HTTP429; it produced no usable review report. Project #6 was read
fully (107 items); #72 is In Progress, with broader Issues open.
