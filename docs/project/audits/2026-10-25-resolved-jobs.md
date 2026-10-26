# Durable RESOLVE jobs orientation — 2026-10-25

Baseline: clean main `7426724078af1038ad8b009b8cccf236e31dec82`, PR243/#20 delivered.
The owner selected durable RESOLVE jobs by instructing continue after that recommendation.
The new written proposal and ADR048 remain unapproved; no runtime change is claimed.

## Advisory and direct evidence

[Read-only hosted audit40250829310](https://github.com/stauntonjr/procurement-intelligence-lab/actions/runs/40250829310)
failed with Gemini HTTP503 on the baseline, one request,82 files, snapshot
`b7145008b52184d0adffaa54ad9e7e6fa17e570cc7100ba55f4dc2d8b146e344`.
It produced no completed advisory report. Earlier successful run40247832626 is a different
baseline/run, not evidence that this provider call succeeded. No provider replacement or automatic
retry was performed.

Direct review read #36 and the broader #13/#21/#33/#35/#37/#41/#42/#39/#43/#45/#68/#70/#75
contracts, delivered #232/#236, ADR045/046, local-job/resolved-execution contracts and the actual
application, platform, bootstrap, CLI and storage paths. Current job definitions/commands/receipts
validate exact five-stage types and identifiers. The resolved runner lacks arrival-guard injection,
and the resolved archive currently opens its own transaction. These are explicit integration
seams for the proposal, not evidence of shipped defects in the existing bounded callers.

Live preflight authenticated stauntonjr. Full Project6 review used limit500:129 items,25 fields,
11 views before new intake. Structural audit captured128 Issues/31 labels/10 milestones with no
missing configured fields, labels, milestones or views. #36 remains In Progress for broader
listener/worker acceptance; #14/#39/#43/#45 and related broader contracts stay open.

The new native child #244 records the bounded direction and proposed contract. Its Project item
is Todo, Decision Needed=Yes pending written approval. This is distinct from an approved or
implemented runtime slice. Duplicate ADR033 numbering and historical demo-priority Issue headers
remain separate planning drift; this proposal does not revise them or close broader work.
