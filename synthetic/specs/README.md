# Synthetic data specification

## Four-project demo corpus

`procurement-corpus-v1.json` defines Atlas, Borealis, Cinder and Delta: six XLSX documents
per project, 40 rows per document, 960 source-row occurrences and 164 scoped unique items.
These synthetic examples share generator ancestry and worksheet layout. They do not establish
production representativeness, parser robustness or model quality.

Regenerate byte-identical workbook, authority and manifest resources with:

```bash
uv run python tools/generate_procurement_corpus.py
```

BOM revisions, independent PO lines, quotes and commitments retain explicit approval, effectivity,
supersession and source identity. The complete scoped inventory reaches existing policies.
Run `uv run python -m procurement_intelligence_lab.interfaces.web` and open `/corpus`.

Evaluator-only `evals/procurement_corpus/v1/manifest.json` pins 48 authored queries, gold and qrels:
24 development, 12 validation and 12 test cases split by project. Forty assess quantities;
eight reject invalid structured requests. Natural-language text is annotation: G1 sends explicitly
authored item/date requests and does not evaluate interpretation, retrieval or agent behavior.
The shared template ancestry limits independence of the project splits.

```bash
uv run python tools/evaluate_procurement_corpus.py --base-url http://127.0.0.1:8765 --output artifacts/procurement-corpus/v1/evaluation.json
```

`pilot-gold-review.json` records an independent original XML/authority audit. The earlier
`gold.json` and `gold-review.json` retain the 12 Atlas regression cases and their historical
first-increment audit; their original manifest hashes describe that earlier revision.
Gold, qrels and query labels are excluded from runtime packages. The twenty-project benchmark
and live operational-agent acceptance remain later gates.
