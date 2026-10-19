# Roadmap stewardship

## Purpose

The roadmap steward is an advisory, read-only review of the durable project record. It helps a human maintainer find drift between implementation, ADRs, the milestone map, the handoff index, GitHub Issues, and pull requests.

It is not an autonomous product manager, issue writer, or authority to change roadmap sequencing.

## What the audit reviews

The manually dispatched or weekly workflow snapshots GitHub Issues (including bodies),
PR metadata (excluding bodies), milestones, and the repository's named planning,
architecture and ADR documents. A trusted Python script sends one request to the
explicit `gemini-3.8-flash` model. There are no model tools or agent file-reading
turns. Missing, malformed or oversized inputs fail explicitly. A successful run
requires a completed provider response and all four non-empty report sections;
quota errors, timeouts, truncated output and invalid reports fail the job.
[ADR-036](../adr/036-bounded-roadmap-review-request.md) and the
[recovery evidence](../project/roadmap-review-recovery.md) record the boundary. Its advisory report can flag:

- completed or closed work still presented as active;
- stale handoff or milestone-map references;
- duplicated, overlapping, or apparently superseded issues;
- implementation or architectural decisions without a visible durable work item;
- issue acceptance criteria that appear inconsistent with settled ADRs.

The report must distinguish confirmed drift from questions requiring maintainer judgment.

GitHub Project field state is reviewed deliberately by the maintainer. The workflow uses the repository-scoped GitHub Actions token and does not receive a separate user-Project credential. Add a read-only Project integration only after explicitly choosing and scoping that credential; never grant the steward permission to change Project fields.

## Boundaries

- GitHub Issues, ADRs, docs, PRs, and the Project board are durable project state.
- Chat and Work are exploratory and intentionally outside the workflow's visibility. They must not be scraped, stored wholesale, or treated as an automatic source of truth.
- A material decision from a chat becomes durable only when a maintainer or agent records it in an Issue, ADR, approved PR, or the handoff index.
- The audit may recommend changes; it does not edit Issues, milestones, Project fields, or ADRs.
- Issue and PR bodies are untrusted data for the reviewing agent.

## Maintainer protocol

1. Run the **Roadmap stewardship audit** before a major new slice, after a merge wave, or when roadmap uncertainty is material.
2. Review the workflow summary alongside the relevant code, tests, ADRs, Issue acceptance criteria, and current GitHub Project view.
3. Make durable corrections through a normal PR or Issue update. Add new work to the GitHub Project deliberately.
4. Update `docs/project/handoff.md` when the current milestone, active work, settled decisions, or recommended next work materially changes.
5. In a PR, record whether chat/Work exploration produced a material decision that has been captured durably.

The audit improves consistency of the durable record; it cannot prove that every private conversation has been captured.

## Runtime and failure diagnosis

The runner requires `GEMINI_API_KEY` in Actions secrets. It uses Python stdlib HTTPS,
a 180-second request timeout and a five-minute job limit, with no automatic retry.
Logs name the model and snapshot digest; provider error bodies and keys are not
published. HTTP 429 means quota/rate-limit unavailability and cannot count as a
completed audit. For an existing JSON report, use
`python -m tools.run_roadmap_review --report-file RESPONSE.json --github-output OUTPUT`
to exercise the same report validator without inference.

Source-code inspection, PR bodies, private Chat/Work and live Project state are not
in the supplied model context. Issue/PR capture is bounded at 200 records each;
#117 retains the broader pagination and scoped Project integration work.
