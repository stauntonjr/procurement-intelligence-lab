# Procurement Intelligence Lab

Procurement Intelligence Lab is a public, synthetic-data reference architecture for trustworthy BOM and procurement intelligence. It turns semi-structured documents into provenance-preserving knowledge, keeps source assertions distinct from truth, reconciles them into operational state, and exposes deterministic and AI-assisted investigation tools.

## Showcase

The showcase is a chat interface paired with an evidence inspector and source viewer. A material answer claim can be opened from calculation, through operational state, reconciliation, canonical entities, resolution decisions, source assertions, mapped fields, document structure, and the original synthetic document. Epistemic status and correction/review actions remain visible.

## Architecture

Artifacts flow through `StructuredDocument → MappedDocument → normalized observations → source assertions → entity mentions → resolution decisions → canonicalized assertions → reconciliation → operational state → derived intelligence`. Postgres is the intended canonical store; search, vector, and graph systems are replaceable projections. Core semantics are framework-independent Python dataclasses behind ports and adapters.

## Status

The initial vertical slice is complete: a dependency-free XLSX BOM adapter, typed line-level evidence, deterministic SKU/GPU/cost queries, explicit cost abstention, source assertions, conservative entity resolution, operational-state projection, reconciliation, and a framework-independent evidence chain.

The current implementation also includes the claims/evidence service and a constrained chat adapter. A dependency-free local HTTP chat/evidence inspector is in progress in [PR #82](https://github.com/stauntonjr/procurement-intelligence-lab/pull/82). Durable identifiers, persistence, review workflows, retrieval projections, and product-feedback capture remain planned.

The canonical delivery map is [docs/development/milestone-map.md](docs/development/milestone-map.md). Changes to architecture or delivery status must follow the synchronization policy in [ADR-012](docs/adr/012-plan-and-milestone-synchronization.md).

## Local entry points

```bash
uv sync --all-groups
make check
make eval
make demo
```

`make demo` is equivalent to `uv run python -m procurement_intelligence_lab`. Pass `--help` to inspect its synthetic-BOM and canonical-candidate inputs.

## Public-data disclaimer

This repository contains no confidential, proprietary, export-controlled, or operational procurement data. Examples and future fixtures must be synthetic or demonstrably public. This is an architectural lab, not a production procurement or decision authority.
