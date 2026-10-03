"""Scoring must reject plausible but unsupported answers and omitted cases."""

from pathlib import Path
from typing import Any

import pytest


def test_frozen_pilot_contract_validates() -> None:
    from tools.evaluate_procurement_corpus import load_dataset

    dataset = load_dataset(Path("evals/procurement_corpus/v1"))
    assert len(dataset["queries"]) == 48


def test_score_rejects_wrong_value_and_missing_evidence() -> None:
    from tools.evaluate_procurement_corpus import score_response

    gold = {
        "http_status": 200,
        "status": "clear",
        "reason": None,
        "required_quantity": "4",
        "ordered_quantity": "4",
        "required_evidence": {
            "governance": [
                {"artifact_id": "x", "row": 2, "location": "quantity", "role": "governance"}
            ]
        },
    }
    response: dict[str, Any] = {
        "status": "clear",
        "reason": None,
        "required_quantity": "4",
        "ordered_quantity": "4",
        "evidence": [
            {"artifact_id": "wrong", "row": 2, "location_kind": "tabular", "evidence_id": "ref"}
        ],
        "evidence_by_role": {"governance": ["ref"]},
    }
    assert score_response(200, response, gold)
    response["evidence"] = [
        {
            "artifact_id": "x",
            "row": 2,
            "location_kind": "tabular",
            "evidence_id": "ref",
            "sheet": "BOM",
            "cells": ["A", "B", "C", "D", "E"],
        }
    ]
    assert not score_response(200, response, gold)
    response["ordered_quantity"] = "5"
    assert score_response(200, response, gold)
    response["ordered_quantity"] = "4"
    response["status"] = "not_assessed"
    assert score_response(200, response, gold)


def test_omitted_query_is_unknown_not_success() -> None:
    from tools.evaluate_procurement_corpus import summarize

    report = summarize(["one", "two"], [{"id": "one", "outcome": "pass", "errors": []}])
    assert report["counts"] == {"pass": 1, "fail": 0, "unknown": 1, "not_applicable": 0}
    assert report["ready"] is False


@pytest.mark.parametrize("mutation", ["version", "duplicate", "orphan", "roles"])
def test_manifest_rejects_invalid_labels(tmp_path: Path, mutation: str) -> None:
    import json
    import shutil
    from hashlib import sha256

    from tools.evaluate_procurement_corpus import load_dataset

    shutil.copytree("evals/procurement_corpus/v1", tmp_path / "data")
    directory = tmp_path / "data"
    manifest = json.loads((directory / "manifest.json").read_text())
    name = "queries.json" if mutation == "duplicate" else "pilot-gold.json"
    value = json.loads((directory / name).read_text())
    if mutation == "version":
        manifest["schema_version"] = "unsupported"
    elif mutation == "duplicate":
        value["queries"].append(value["queries"][0])
    elif mutation == "orphan":
        value["cases"][0]["id"] = "missing-query"
    else:
        value["cases"][0]["required_evidence"] = {}
    (directory / name).write_text(json.dumps(value))
    manifest["hashes"][name] = sha256((directory / name).read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        load_dataset(directory)


@pytest.mark.parametrize("payload", [None, [], {"evidence": [None]}])
def test_malformed_response_keeps_all_query_results(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    from tools import evaluate_procurement_corpus as evaluator

    def fetch(url: str) -> tuple[int, object]:
        return 200, payload

    monkeypatch.setattr(evaluator, "_fetch", fetch)
    report = evaluator.evaluate("http://unused.invalid")
    assert len(report["results"]) == 48
    assert report["ready"] is False
    assert report["counts"]["unknown"] == 48


def test_wrong_sheet_and_cells_cannot_support_correct_answer() -> None:
    from tools.evaluate_procurement_corpus import score_response

    gold = {
        "http_status": 200,
        "status": "clear",
        "reason": None,
        "required_quantity": "4",
        "ordered_quantity": "4",
        "required_evidence": {
            "governance": [
                {"artifact_id": "x", "row": 2, "location": "quantity", "role": "governance"}
            ]
        },
    }
    response: dict[str, Any] = {
        "status": "clear",
        "reason": None,
        "required_quantity": "4",
        "ordered_quantity": "4",
        "evidence": [
            {
                "artifact_id": "x",
                "row": 2,
                "sheet": "wrong",
                "cells": ["B"],
                "location_kind": "tabular",
                "evidence_id": "ref",
            }
        ],
        "evidence_by_role": {"governance": ["ref"]},
    }
    assert score_response(200, response, gold)


def test_missing_authority_record_rejected() -> None:
    from tools.evaluate_procurement_corpus import validate_source

    expected = {
        "artifact_id": "x",
        "role": "approved_bom_revision",
        "quantity": "4",
        "authority_record": {"row": 2, "approved_at": "2026-01-01T00:00:00Z"},
    }
    ref = {
        "artifact_id": "x-authority",
        "location_kind": "record",
        "record_key": "2",
        "collection": "records",
    }
    source = {
        "evidence": ref,
        "authority": {
            "document": {
                "project_id": "atlas",
                "artifact_id": "x",
                "role": "approved_bom_revision",
            },
            "record": {},
        },
    }
    assert validate_source(source, ref, expected, "atlas", "GPU-A")


def test_foreign_authority_scope_is_rejected() -> None:
    from tools.evaluate_procurement_corpus import validate_source

    ref = {"artifact_id": "x-authority", "location_kind": "record", "collection": "records"}
    expected = {"artifact_id": "x", "role": "approved_bom_revision", "authority_record": {"row": 2}}
    source = {
        "evidence": ref,
        "authority": {
            "document": {
                "project_id": "atlas",
                "artifact_id": "x",
                "role": "approved_bom_revision",
                "tenant_id": "foreign",
                "site_id": "foreign",
            },
            "record": {"row": 2},
        },
    }
    assert validate_source(source, ref, expected, "atlas", "GPU-A")
