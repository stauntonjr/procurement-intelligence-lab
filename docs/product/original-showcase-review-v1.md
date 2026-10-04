# Original showcase review v1

Unmerged continuation of #71, part of #53/#66/#67/#68/#70/#72/#74.
[ADR-033](../adr/033-original-showcase-source-injection.md) defines source injection.
The original January fixtures now use the existing exact-review workflow. They remain
fixed synthetic snapshots with original claim, policy and evidence identities.

Configure sources before starting the server; neither HTTP requests nor model proposals
can select a source set. `--sources corpus` remains the default with existing project,
cutoff and assessed-order semantics. Original configurations require `--project synthetic-project`,
item `GPU-A` and aware cutoff `2026-01-15T00:00:00Z`. Other original items/dates fail before
business assessment. The scope is `synthetic-tenant/synthetic-project/synthetic-site`.

| Sources option | Admitted workbooks | Required | Order observation | Assessment |
|---|---|---|---|---|
| showcase-a-order | revision A and short order | 4 | 2 | anomaly |
| showcase-a-b-order | revisions A/B and short order | unresolved | 2 | not_assessed / unresolved_requirement |
| showcase-a-only | revision A | 4 | absent | not_assessed / missing_observation |

The unresolved case retains an observed 2; this is source data, not an assessed or reconciled
quantity. Saving a brief records human review without resolving any source conflict.
Original XLSX bytes and legacy routes are unchanged. Admission verifies packaged hashes,
scope and permissions; missing, corrupt or foreign sources cannot supply confident results.

Use the private token-file setup in [browser review](local-browser-review-v1.md), then:

```bash
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.review_web \
  --database /tmp/original-a-order.db --project synthetic-project \
  --sources showcase-a-order --token-file /tmp/reviewer-token --port 8001 \
  --model-endpoint http://127.0.0.1:8000/v1
```

Omit `--model-endpoint` for typed fixture mode with zero inference. For the CLI:

```bash
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.live_review \
  --database /tmp/original-a-order.db --project synthetic-project --sources showcase-a-order \
  ask --question 'Compare GPU-A orders with its governing requirement and show evidence.' \
  --as-of 2026-01-15T00:00:00Z
```

Use a separate database for each source set. Recovery and exact approval must use the same
source selection and immutable application/model/prompt/tool versions; incompatible runs are
refused before tools. Authenticated human approval remains the only save authority.
Source-set names, expected quantities, outcome labels and evaluation metadata never enter
model input. There is one interpretation attempt per submission, no automatic inference retry.
See [actual installed browser evidence and limits](../project/original-showcase-live.md).
