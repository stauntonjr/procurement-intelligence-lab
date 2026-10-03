"""Independent first-project inventory and evaluator isolation contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_first_project_source_inventory() -> None:
    from procurement_intelligence_lab.adapters.xlsx import read_bom

    directory = ROOT / "src/procurement_intelligence_lab/examples/corpus_v1"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["schema_version"] == "procurement-demo-corpus/v1"
    assert {d["project_id"] for d in manifest["documents"]} == {"atlas"}
    assert len(manifest["documents"]) == 6
    for doc in manifest["documents"]:
        assert len(read_bom(directory / doc["path"]).lines) == 40
    assert not any(
        p.name in {"gold.json", "queries.json", "qrels.json"} for p in directory.rglob("*")
    )


def test_gold_has_explicit_source_arithmetic() -> None:
    gold = json.loads((ROOT / "evals/procurement_corpus/v1/gold.json").read_text())
    assert len(gold["cases"]) == 12
    assert gold["scope"] == "one-project-development-only"
    assert all(case["source_arithmetic"] and case["source_rows"] for case in gold["cases"])
