# Issue244: durable local RESOLVE jobs

Primary M1; native child of #36. The owner approved design36b9378, accepted ADR048 and the
[six-task plan](../../../superpowers/plans/2026-10-25-resolved-prefix-jobs.md). The
[public contract](../../../architecture/local-resolved-prefix-jobs.md) defines the separate
six-stage profile. Issue244 records protected delivery, installed main proof and final Project
state; branch qualification alone does not establish main acceptance.

The [legacy comparison](legacy-comparison.py) runs baseline7426724 and candidate public callers
against identical source paths/bytes, code/context pins and an injected fixed public-main clock.
It compares complete JSON, old job/archive codec graphs and RESOLVE rejection payloads without
removing receipt fields, offsets, identifiers or dispositions. This artificial clock is confined
to exact compatibility comparison. Ordinary public/restart/installed probes use the shipped clock.

The [artifact qualifier](qualify_artifacts.py) installs the built wheel into new base and storage
virtual environments on Python3.12 and3.13. Each starts outside the checkout with `python -I`,
no PYTHONPATH/PYTHONHOME, and checks actual site-packages imports and every installed package file
against wheel/source bytes. Base probes run six actual stages and verify missing storage is a
typed unavailable response. Storage probes first inventory product/storage dependencies, then
install disclosed pytest/Hypothesis tools and copy tests only (no product source). Each runs all74
new/old public command cases, including every advertised operation, deleted-input recovery,
acknowledgement loss and killed-process restart. The injected restart faults are test-only.

Synthetic source example: row7 SKU `GPU-A`, one explicit scoped catalog key `GPU-A`, normalized
exact match → canonical `GPU-A`, status `resolved`, source-row evidence retained. Empty, ambiguous,
missing and duplicate/numeric cases are covered separately; successful execution does not imply
all mentions resolved. This qualifies declared engineering behavior, not held-out matching quality,
production readiness or completion of broader #36/M3.

All storage is an explicitly selected task-owned disposable Postgres server with independent
fixture schemas. No shared workloads are restarted. Receipts omit DSNs/credentials. No matching
algorithm/model changed and no previously shipped semantic defect was repaired, so existing31
challenge/known-bad pairs are retained without a new defect challenge. Current versus first-retained
source/prefix/resolved/attempt evidence stays explicit. No worker/queue/lease/automatic retry,
RECONCILE job, fresh seven-stage execution or new operational authority is added.
