# Roadmap review recovery — 2026-10-19

Issue #199; primary milestone M0. [ADR-036](../adr/036-bounded-roadmap-review-request.md)
records the single-request boundary and declared snapshot scope.

## Observed baseline

- Hosted run [39331080447](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/39331080447)
  failed: Gemini CLI exit 173, HTTP 429, `gemini-3.6-flash` daily free-tier request
  quota exhausted. No valid report. Unavailable tool calls were also observed.
- The existing OpenAI credential authenticated for model discovery but an actual
  `gpt-5.3-codex` inference probe returned `credit_balance_exhausted`. No replacement
  credential was published or deployed. Copilot has no configured CI credential.
- A minimal `gemini-3.8-flash` request succeeded. The first full snapshot failed
  HTTP 429 because its 384,446 input tokens exceeded the 250,000/minute allowance.
  PR bodies accounted for most avoidable volume; the revised scope explicitly
  retains PR metadata while keeping full Issue bodies and architecture documents.

## Acceptance boundary

The candidate must produce the four non-empty sections from the real hosted
workflow. Its findings are checked against the named source records. Deterministic
CLI tests reject missing, malformed, empty-section, quota-error and truncated
responses. C029 rejects the historical empty-section validator defect.

This is availability and contract evidence over public repository data, not a
blind quality benchmark. Project metadata, source-code inspection, private chats,
and PR-body review are excluded. The snapshot capture still limits Issues/PRs to
200 each; #117 owns broader coverage. Quota is shared and can still be exhausted.

## Observed candidate results

- Local single-request generation produced a valid report; independent focused
  report/CLI/configuration tests passed (22 tests). C029's known-bad empty-section
  validator was rejected.
- Hosted candidate [39332909508](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/39332909508)
  passed on `02773ee`; the final prompt candidate
  [39333042580, attempt 2](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/39333042580/attempts/2)
  passed on `bd67827`. Attempt 1 returned HTTP 503 and correctly failed. The
  successful rerun was deliberately requested by the maintainer agent; the runner
  does not silently retry or substitute providers.
- Manual grounding confirmed the #109 checklist references to closed #112/#115,
  stale branch-status headers in ADR-032/ADR-033, and the ADR-033 numbering collision.
  The model's historical handoff contradiction claim needs qualification because
  the handoff contains an explicit superseding integration notice. Its inferred
  missing Issue linkage for PR #195 is rejected: that PR body names #74, and PR
  bodies are outside this snapshot. These limitations are retained, not scored as
  correct findings or silently converted into planning changes.
- This restores report production and admission, not autonomous roadmap authority
  or error-free audit quality. Reviewers must check suggested findings against the
  full sources before changing Issues or roadmap records. Latest-revision checks
  and merge/runtime disposition are retained in PR #200's semantic evidence.
