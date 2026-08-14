# Evaluation plan

Technology evaluations are tracked in the [technology evaluation register](evaluation/technology-register.md). Current entries are bounded experiments, not runtime adoption decisions.

## Offline quality

- Entity resolution: precision/recall by entity type, with a “review” class for ambiguous pairs.
- Retrieval: Recall@k and nDCG on questions requiring item, vendor, date, and source constraints.
- Extraction: field-level precision, recall, and abstention rate against adjudicated fixtures.
- Anomaly detection: precision at alert budget, time-to-detection, and explanation completeness.

## Operational quality

- Freshness from source capture to searchable state.
- p50/p95 query latency and ingestion throughput under replayed representative load.
- Duplicate action rate, approval bypass rate, and audit completeness.
- Human review minutes per accepted alert and disagreement rate.

## Safety gates

- No external write in evaluation mode.
- Cross-project retrieval tests must fail closed.
- Prompt-injected document text must not change tool authorization.
- Every answer must be able to show source evidence or explicitly abstain.

The first useful benchmark is small, versioned, and labeled. A larger dataset without adjudication would produce false confidence.
