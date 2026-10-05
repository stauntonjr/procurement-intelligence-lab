# Local Qwen interpretation execution increment

Approved parent: [corpus demo execution plan](2026-10-03-procurement-demo-corpus.md), Tasks 5B/5C.
Primary M5 / #53; acceptance #72; governing #66/#67/#68/#70/#71. User selected the
already-loaded Qwen 3.6 on DGX. Reuse it; do not provision inference or change GPU allocation.

1. Specify ADR-032 and the six-field contract. Add strict interpretation and adapter tests RED.
2. Implement one local model request behind a port, application-owned interpretation journal,
   and entry into the existing serial workflow using the same immutable run. No model arithmetic,
   approvals, arbitrary SQL, free-form factual drafting, retries or trace upload.
3. Exercise the actual CLI and authenticated local HTTP boundary, including clarification,
   malformed response, scope/date binding, interruption/recovery and exact approval. Preserve fixture defaults.
4. Freeze configuration; run three repetitions of mismatch, unresolved requirement and missing
   order through the real installed application with live inference, compare deterministic facts
   and source references. Report individual outcomes/calls/tokens/latency; no broad quality claim.
5. Run full checks, clean-wheel probes and existing challenges; one independent whole-slice review,
   one author correction pass if needed. Publish stacked PR and revision-bound semantic evidence;
   update durable handoff and GitHub planning. Browser interaction/deployment remain separate gates.

## Contract

- Inputs: authenticated server-owned owner/scope and aware as-of date, bounded question, scoped
  admitted item catalog, immutable provider/model/prompt/tool/fixture/application versions.
- Output: clarify/unsupported/typed failure, or exact canonical deterministic review brief.
- Scope/as-of: model proposal must match the caller's explicit project and as-of and admitted item;
  ambiguity cannot select a default item/date or grant authority.
- Policy: one call, max 256 output tokens, temperature 0, no thinking, timeout 30 seconds;
  existing tools and human receipts exclusively govern facts and saves. Local loopback only.
- Evidence: same run/query/attempt identities; question hash, interpreted fields, safe reason code,
  received token usage or unknown, elapsed time, failure code, actual tool events and exact brief.
  No raw response/reasoning, secrets, prompts containing gold, or remote telemetry.
- Failures: malformed/extra/duplicate fields, mismatched scope/date, unavailable model, timeout,
  unknown interrupted attempt and journal/checkpoint errors remain explicit; no silent fallback.

## Scenarios

Empty/missing/unknown: empty question rejected; ambiguous item/date clarify; missing order stays unknown.
Multiplicity/conflict: many catalog entries never default; unresolved requirements preserved.
Scope/time: wrong owner/project/date, naive date, future dates, changed versions fail or clarify.
Numeric boundaries: zero/negative/fractional token budgets invalid; no model quantities accepted;
existing corpus quantities remain authoritative, including zero/fractional observations.
Unsupported/malformed: unsupported task, schema extras/duplicates, bad response/usage, timeout.
Public/artifact: real subprocess CLI, local authenticated HTTP, installed wheel, restart/repeat save.
Safe counterexample: valid scoped interpretation yields baseline facts; model approval text cannot save.
