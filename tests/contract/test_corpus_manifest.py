"""Independent first-project inventory and evaluator isolation contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_first_project_source_inventory() -> None:
    from procurement_intelligence_lab.adapters.xlsx import read_bom

    directory = ROOT / "src/procurement_intelligence_lab/examples/corpus_v1"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["schema_version"] == "procurement-demo-corpus/v1"
    atlas = [d for d in manifest["documents"] if d["project_id"] == "atlas"]
    assert len(atlas) == 6
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


def test_pilot_inventory_and_split_isolation() -> None:
    from collections import Counter

    directory = ROOT / "src/procurement_intelligence_lab/examples/corpus_v1"
    runtime = json.loads((directory / "manifest.json").read_text())
    assert Counter(doc["project_id"] for doc in runtime["documents"]) == {
        "atlas": 6,
        "borealis": 6,
        "cinder": 6,
        "delta": 6,
    }
    evaluation = ROOT / "evals/procurement_corpus/v1"
    manifest = json.loads((evaluation / "manifest.json").read_text())
    queries = json.loads((evaluation / "queries.json").read_text())["queries"]
    assert len(queries) == 48
    splits = manifest["project_splits"]
    assert Counter(splits[q["project"]] for q in queries) == {
        "development": 24,
        "validation": 12,
        "test": 12,
    }
    for project in splits:
        assert Counter(q["category"] for q in queries if q["project"] == project) == {
            "exact_identifier": 3,
            "paraphrase": 3,
            "temporal_revision": 2,
            "missing_conflicting": 2,
            "unsupported_ambiguous": 2,
        }
