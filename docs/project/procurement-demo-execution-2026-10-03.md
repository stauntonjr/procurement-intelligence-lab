# Demo execution: first corpus increment

Primary implementation issue: #29; part of #12/#27/#71/#73. Branch: `codex/demo-corpus-pilot`.
The four-project corpus, operational agent, and retrieval experiments remain uncompleted gates.

## Baseline and public recovery

Baseline `b0cc77ef66e913161d143cf25691655064d5b5f8` passed 353 tests. Live #60 is closed via PR #174;
stale handoff/milestone statements were corrected. Planning preflight authenticated `stauntonjr`;
audit found 106 Issues, 107 Project items, 31 labels, 10 milestones, 25 fields and 11 views,
with no missing configured fields/labels/milestones/views. The automated roadmap run 37129799497
failed upstream quota/service errors; it is not successful roadmap evidence.

The public 404 was traced to the absence of the `procurement-inspector` container. Its original
image and clean deployment checkout still existed; why the container disappeared is not established.
Recreated only `inspector` with `docker compose -f deploy/compose.yml up -d --no-build --no-deps inspector`,
using `PROCUREMENT_INSPECTOR_REVISION=f9346a5c15807ccea73661734e272c730936ad51`.
Traefik and unrelated services were left running. Public root and HTTPS health recovered. Headless Chromium verified the shipped shared-value
answer and an actual original GPU-A source click.
This restored release predates the corpus branch and current main; it is not the new demo release.

## First increment contract

ADR-027 governs neutral admission, authority-source lookup and runtime/gold separation. One project
contains six 40-row workbooks (240 source-row occurrences), 240 authority records and 12 independently
reviewed gold cases. No model or search ranking participates. Unknown, unresolved and absent remain
distinct from zero. Order snapshot replacement/expiry is explicitly unsupported at admission;
independent lines sum, exact replays deduplicate, conflicting line assertions abstain.

The browser at `/corpus` uses the shipped `/api/corpus/investigate` and `/api/corpus/source` paths.
Queries cannot grant tenant/site permissions or bypass the server's project allowlist. Responses
retain policy/snapshot/assessment identities, exact quantities, candidate/input dispositions and
original-cell plus authority evidence. Every request revalidates admitted source hashes.

Independent review corrected the before-effective-boundary gold reason to `missing_observation`
while retaining `rejected_future` line dispositions. Review also found duplicate worksheet row
coordinates, now rejected before fact creation; the fixture and product review are distinct.

## Acceptance status

Branch validation is recorded in the semantic evidence artifact and PR. Independent gold review
accepted all 12 cases. Browser checks cover original quantity/authority selection, match, conflict,
missing evidence, unknown-item recovery, and delayed-response ordering for both queries and sources.
Clean-wheel checks install into two separate environments outside the checkout, resolve original
sources, compare stable identities, and exclude evaluator material. Do not infer
main, public deployment, G1 four-project acceptance, or live-agent acceptance from this document.

Final local verification: `make check` passed 385 tests with 90.15% combined coverage and the
coverage ratchet; `make package-smoke` passed; C001-C016 known-bad challenges were rejected.
Independent semantic review has no unresolved findings. These are first-increment results.
