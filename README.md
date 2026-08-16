# Procurement Intelligence Lab

Procurement Intelligence Lab is a public, synthetic-data reference architecture for trustworthy BOM and procurement intelligence. It turns semi-structured documents into provenance-preserving knowledge, keeps source assertions distinct from truth, reconciles them into operational state, and exposes deterministic and AI-assisted investigation tools.

Reusable semantic contracts and DomainPackage compilation live under `platform/`; procurement-owned
BOM, BoQ, Purchase Order, state, reconciliation, and anomaly behavior lives under
`domains/procurement/`. See [platform semantics and vertical ownership](docs/architecture/platform-semantics.md).

## Showcase

The showcase is a chat interface paired with an evidence inspector and source viewer. A material answer claim can be opened from calculation, through operational state, reconciliation, canonical entities, resolution decisions, source assertions, mapped fields, document structure, and the original synthetic document. Epistemic status and correction/review actions remain visible.

## Architecture

Artifacts flow through StructuredDocument → MappedDocument → normalized observations → source assertions → entity mentions → resolution decisions → canonicalized assertions → reconciliation → operational state → derived intelligence. Postgres is the intended canonical store; search, vector, and graph systems are replaceable projections. Core semantics are framework-independent Python dataclasses behind ports and adapters.

## Project memory and status

The repository is the canonical interoperability layer across ChatGPT, Work, Codex, humans, and other development agents. Use [docs/project/handoff.md](docs/project/handoff.md) as the concise fresh-agent index, then follow its links to the authoritative milestone map, ADRs, architecture docs, Issues, and PRs. Chat/Work supports exploration and planning; development agents implement against the repo; GitHub artifacts carry durable shared state.
## Use-case anchors

The first synthetic showcase is organized around three procurement questions:

- which distinct SKUs are required for the next data center;
- how many GPUs are required, ordered, received, and outstanding;
- what a proposed BOM would cost, with explicit prices, assumptions, and missing evidence.

See [the use-case and query contracts](docs/product/use-cases.md) for their evidence, ambiguity, and evaluation requirements.

## Status

The initial evidence-first vertical capabilities are runnable, but the encompassing GitHub milestones remain acceptance-driven and are not implied complete by merged slices. The repository includes a coordinate-aware XLSX adapter, typed line-level evidence, conservative entity resolution, explicit reconciliation precedence, governed claims, constrained chat routing, and a local HTTP inspector with source lookup and reproducible review context.

The M0 semantic-quality harness now separates unit, contract, integration, and regression tests; performs clean-wheel and real HTTP happy-path checks; and records nine shipped-defect challenges (C001-C009) under `evals/development_agents/challenges/`. `make challenges` requires every oracle to pass on current code and reject its executable known-bad mutation.

M7 now includes the append-only assertion-ledger boundary, timezone-aware as-of reads, the first evidence-backed anomaly taxonomy, and an injectable execution/decision provenance contract. The example execution manifest shows how resolved Compose/configuration values become immutable run and component identities. Durable database storage, broader anomaly orchestration, temporal correction events, retrieval projections, and product-feedback persistence remain later slices.

The canonical delivery map is docs/development/milestone-map.md. Changes to architecture or delivery status must follow the synchronization policy in ADR-012.

## Local entry points

    uv sync --all-groups
    make check
    make eval
    make package-smoke
    make challenges
    make demo

make demo is equivalent to uv run python -m procurement_intelligence_lab. Pass --help to inspect its synthetic-BOM and canonical-candidate inputs.

## Public-data disclaimer

This repository contains no confidential, proprietary, export-controlled, or operational procurement data. Examples and future fixtures must be synthetic or demonstrably public. This is an architectural lab, not a production procurement or decision authority.
