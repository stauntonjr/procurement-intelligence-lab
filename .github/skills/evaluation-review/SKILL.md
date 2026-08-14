---
name: evaluation-review
description: Review PRs that claim improvements to extraction, entity resolution, retrieval, ranking, prompts, models, forecasts, or agents. Verify benchmark evidence and regression risk.
---

# Evaluation review

For any PR that changes an intelligent or probabilistic component:

1. Identify the claimed improvement and the current baseline.
2. Verify the evaluation corpus and version are named and representative of the claim.
3. Verify the candidate run records git SHA, configuration, model/prompt/schema versions, and seed where meaningful.
4. Check task-specific metrics and important asymmetric errors:
   - document structuring: OCR/text, table/cell/row-column reconstruction, reading order as applicable;
   - schema mapping: field accuracy/F1 and row grouping separately from structure quality;
   - entity resolution: candidate recall, pair/decision precision-recall, false merges, review rate, calibration where relevant;
   - retrieval/reranking: Recall@K, MRR/nDCG or task-appropriate metrics plus error inspection;
   - agents: tool-selection/task success, evidence support, abstention, authorization/action correctness;
   - forecasts: discrimination/calibration/error intervals and temporal leakage checks as appropriate.
5. Confirm the PR does not improve one headline metric by causing an unacceptable regression elsewhere (latency, cost, precision, false merges, safety, or review load).
6. Require representative error examples or an error-analysis artifact for material algorithm changes.
7. Do not accept “prompt is clearer,” “model is newer,” or “framework is popular” as quality evidence.
8. If evidence is incomplete, recommend an experiment rather than an architectural commitment.
