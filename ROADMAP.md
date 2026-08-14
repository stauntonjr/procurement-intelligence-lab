# Roadmap

## 0. Portfolio slice (this repository)

- Establish an evidence-first domain model.
- Demonstrate deterministic normalization, resolution, retrieval, anomaly detection, and approval gating.
- Make non-claims and evaluation boundaries explicit.
- Enforce semantic contracts with layered CI, clean-artifact smoke tests, and C001-C008 development-agent challenges.

## 1. Discovery-ready prototype

- Add a small relational store with migrations and typed contracts.
- Add document chunking with page/section coordinates and content hashes.
- Compare lexical retrieval with an embedding-backed index on a labeled query set.
- Add a review UI for resolution candidates and anomaly explanations.

## 2. Team-scale pilot

- Introduce connectors behind per-source adapters and replayable ingestion jobs.
- Add temporal event modeling and late-arriving correction handling.
- Calibrate risk scores by project phase and measure alert burden.
- Integrate identity, authorization, secrets rotation, and centralized audit storage.

## 3. Production hardening

- Define SLOs, data retention, deletion, lineage, and incident response.
- Load test ingestion and retrieval with representative—not fabricated—volumes.
- Run red-team exercises against prompt injection, cross-tenant access, and action replay.
- Gate rollout on offline and shadow-mode evaluation, not demo quality.
