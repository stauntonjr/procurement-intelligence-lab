# ADR-036: Bound roadmap stewardship to one evidence-snapshot request

Status: accepted

## Context

Issue #199 follows failed audit run 39331080447. Gemini CLI used its implicit
`gemini-3.6-flash` default and exhausted the 20-request daily free-tier quota; its
agent also attempted unavailable tools. The audit should not spend one inference
turn per file read. A Codex replacement was investigated, but the available OpenAI
API credential returned `credit_balance_exhausted` on an actual inference probe.
No credential was copied into GitHub and no Codex workflow was activated.

## Decision

Use one stdlib HTTPS `generateContent` request to explicitly selected
`gemini-3.8-flash`, with no tools, callbacks, automatic retries or agent runtime.
The trusted script constructs a deterministic JSON snapshot of full Issue bodies,
PR metadata (title/state/merge information, excluding bodies), milestones, and
named planning/architecture/ADR files. PR bodies and code are outside audit scope.
Missing/invalid inputs and oversized snapshots fail rather than silently truncate.
The current capture limit is 200 Issues and 200 PRs; Project integration and larger
snapshot coverage remain under #117.

The model receives no GitHub credentials or mutation capability. The provider key
is passed in an HTTP header only and is never placed in a URL, report or log.
Checkout credentials are not persisted. There is a 180-second HTTP timeout and a
five-minute job timeout. HTTP quota errors are explicit failures, not green reports.
The API's completed response must contain the four required report sections with
non-empty bodies. Blocked/truncated responses, thoughts-only output and malformed
JSON fail closed. Model/snapshot digest/file count are logged for reproducibility.

## Evidence and limits

The original unavailable baseline and candidate runs are recorded in
[roadmap review recovery](../project/roadmap-review-recovery.md). The first complete
snapshot exceeded the observed 250,000 input-token/minute quota (384,446 tokens),
so PR bodies were removed from the declared audit scope. This is a bounded
availability and report-contract comparison, not a general model-quality ranking.
The result remains advisory and requires source checking by the maintainer.

## Consequences

No npm agent installation, shell/tool invocation or model-controlled file access
is needed. Quota exhaustion can still occur if other clients consume the shared
project allowance; this design minimizes requests and does not promise unlimited
availability. Codex/Copilot remain possible future providers with funded/scoped CI
credentials and equivalent acceptance evidence. No provider fallback is silent.
