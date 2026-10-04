"""Evaluator-only natural-language expectations, separate from structured gold."""

import json
from collections import Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from tools.evaluate_procurement_corpus import DATASET, ROOT, load_dataset
from tools.evaluate_procurement_corpus import summarize as structured_summary

PILOT = ROOT / "evals/operational_agents/g2-pilot-v1.json"
OUTCOMES = ("pass", "fail", "unknown", "not_applicable")


def load_pilot(dataset: Path = DATASET, manifest: Path = PILOT) -> list[dict[str, Any]]:
    frozen = json.loads(manifest.read_bytes())
    data = load_dataset(dataset)
    if (
        type(frozen.get("schema_version")) is not int
        or frozen.get("schema_version") not in (1, 2)
        or frozen.get("queries_sha256")
        != sha256((dataset / "queries.json").read_bytes()).hexdigest()
    ):
        raise ValueError("interpretation manifest differs from frozen queries")
    if frozen["schema_version"] == 1 and set(frozen) != {
        "schema_version",
        "queries_sha256",
        "contract",
        "cases",
    }:
        raise ValueError("legacy manifest cannot claim fresh provenance")
    if frozen["schema_version"] == 2:
        from tools.fresh_g2_cohort import validate_fresh

        validate_fresh(dataset, manifest)
    rows = frozen["cases"]
    ids = [r["id"] for r in rows]
    by_id = {q["id"]: q for q in data["queries"]}
    if len(ids) != 48 or len(set(ids)) != 48 or set(ids) != set(by_id):
        raise ValueError("exactly the 48 frozen queries required")
    cases = []
    for row in rows:
        if set(row) != {"id", "expected"} or row["expected"] not in (
            "investigate",
            "clarify",
            "unsupported",
        ):
            raise ValueError("closed evaluator-only expectation required")
        q = by_id[row["id"]]
        cases.append(
            {
                "id": q["id"],
                "question": q["text"],
                "project": q["project"],
                "as_of": q["request"]["as_of"],
                "item": q["request"]["item"],
                "category": q["category"],
                "split": data["manifest"]["project_splits"][q["project"]],
                "expected": row["expected"],
                "request": q["request"],
            }
        )
    return cases


def score_intent(case: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
    call, view = outcome.get("interpretation"), outcome.get("workflow")
    if not isinstance(call, dict) or call.get("status") != case["expected"]:
        return ["interpretation_status"]
    if case["expected"] != "investigate":
        return [] if view is None else ["unexpected_workflow"]
    errors = []
    if call.get("item") != case["item"]:
        errors.append("item")
    try:
        if datetime.fromisoformat(call["as_of"]) != datetime.fromisoformat(case["as_of"]):
            errors.append("as_of")
    except (ValueError, KeyError, TypeError):
        errors.append("as_of")
    if not isinstance(view, dict):
        return errors + ["missing_workflow"]
    if view.get("execution_kind") != "live":
        errors.append("execution_kind")
    if not call.get("run_id") or view.get("run_id") != call["run_id"]:
        errors.append("run_binding")
    brief = view.get("brief")
    run = brief.get("run") if isinstance(brief, dict) else None
    if not isinstance(run, dict) or run.get("project_id") != case["project"]:
        errors.append("scope")
    return errors


def summarize(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    if any(r.get("outcome") not in OUTCOMES for r in results):
        raise ValueError("closed outcome required")
    report = structured_summary([c["id"] for c in cases], results)
    metadata = {c["id"]: c for c in cases}
    for field in ("project", "category", "split"):
        grouped = {}
        for key in sorted({c[field] for c in cases}):
            counts = Counter(
                r["outcome"] for r in report["results"] if metadata[r["id"]][field] == key
            )
            grouped[key] = {name: counts[name] for name in OUTCOMES}
        report["by_" + field] = grouped
    return report
