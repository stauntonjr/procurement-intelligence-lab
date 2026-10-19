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
