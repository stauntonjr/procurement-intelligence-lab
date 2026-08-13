# Database conceptual model

Layers: (1) source artifacts and document structure; (2) interpretation and mappings; (3) append-oriented source assertion ledger; (4) canonical procurement entities and relationships; (5) intelligence such as derived facts, anomalies, and forecasts; (6) review and operational actions.

Postgres is canonical. Search, vector, and graph stores are rebuildable projections/indexes, not independent truth. The assertion ledger is append-oriented for traceability and correction; this does not turn the whole system into generic event sourcing. Canonical state is a governed, queryable projection with explicit reconciliation decisions.

