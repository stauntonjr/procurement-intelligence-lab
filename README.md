# Procurement Intelligence Lab

Procurement Intelligence Lab is a public, synthetic-data reference architecture for trustworthy BOM and procurement intelligence. It turns semi-structured documents into provenance-preserving knowledge, keeps source assertions distinct from truth, reconciles them into operational state, and exposes deterministic and AI-assisted investigation tools.

## Showcase

The intended showcase is a chat interface paired with an evidence inspector and source viewer. A material answer claim can be opened from calculation, through operational state, reconciliation, canonical entities, resolution decisions, source assertions, mapped fields, document structure, and the original synthetic document. Epistemic status and correction/review actions remain visible.

## Architecture

Artifacts flow through `StructuredDocument → MappedDocument → normalized observations → source assertions → entity mentions → resolution decisions → canonicalized assertions → reconciliation → operational state → derived intelligence`. Postgres is the canonical store; search, vector, and graph systems are projections. Core semantics are framework-independent Python dataclasses behind ports and adapters.

## Status

M0 is the engineering and architecture harness. Product behavior is intentionally not implemented. The first tiny implementation target is one synthetic XLSX BOM parsed into intermediate/domain structures and displayed or persisted through a CLI.

## Local entry points

```bash
uv sync --all-groups
make check
make eval
make demo
```

## Public-data disclaimer

This repository contains no confidential, proprietary, export-controlled, or operational procurement data. Examples and future fixtures must be synthetic or demonstrably public. This is an architectural lab, not a production procurement or decision authority.

