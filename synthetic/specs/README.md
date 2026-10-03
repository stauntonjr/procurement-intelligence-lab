# Synthetic data specification

M0 defines only the plan: a small BOM workbook and companion procurement documents with stable artifact IDs, document locations, expected fields, deliberate conflicts, ambiguous mentions, units, dates, and gold evidence links. No full dataset is committed yet.


## First demo corpus increment

`procurement-corpus-v1.json` contains source facts for one project (`atlas`), six XLSX documents,
and 240 source-row occurrences. These are synthetic development examples, not distinct entity
counts or a representative production corpus. BOM revisions, independent PO lines, quotes and
commitments share item identifiers; role, approval, effectivity and supersession stay explicit.

Regenerate byte-identical workbook/authority/manifest resources with:

```bash
uv run python tools/generate_procurement_corpus.py
```

Twelve manually authored expectations live in `evals/procurement_corpus/v1/gold.json`; their
independent original-cell audit is `gold-review.json`. They are not read by the generator or
runtime. The first increment has no validation/test split or retrieval-quality claim. The planned
four-project / 48-query split and twenty-project benchmark remain subsequent gates.

Run `uv run python -m procurement_intelligence_lab.interfaces.web` and open `/corpus` for scoped
item/date investigation. The complete admitted item inventory reaches existing policies; both
XLSX cells and authority JSON are inspectable. Gold and query labels are excluded from the wheel.
