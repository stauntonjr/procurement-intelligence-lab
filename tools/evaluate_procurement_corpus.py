"""Score frozen, oracle-bound structured HTTP cases; no model or retrieval quality claim."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals/procurement_corpus/v1"


def load_dataset(directory: Path) -> dict[str, Any]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("schema_version") != "procurement-corpus-eval/v1":
        raise ValueError("unsupported evaluation schema")
    runtime = ROOT / "src/procurement_intelligence_lab/examples/corpus_v1/manifest.json"
    if sha256(runtime.read_bytes()).hexdigest() != manifest.get("runtime_manifest_sha256"):
        raise ValueError("runtime dataset differs from frozen evaluation inputs")
    values = {}
    for name in ("queries.json", "pilot-gold.json", "qrels.json"):
        raw = (directory / name).read_bytes()
        if sha256(raw).hexdigest() != manifest["hashes"][name]:
            raise ValueError("evaluation hash mismatch")
        values[name] = json.loads(raw)
        if values[name].get("schema_version") != 1:
            raise ValueError("unsupported label schema")
    queries = values["queries.json"]["queries"]
    gold = values["pilot-gold.json"]["cases"]
    qrels = values["qrels.json"]["qrels"]
    ids = [q["id"] for q in queries]
    if len(ids) != 48 or len(set(ids)) != 48:
        raise ValueError("pilot requires 48 unique queries")
    for rows, key in ((gold, "id"), (qrels, "query_id")):
        if len(rows) != 48 or {r[key] for r in rows} != set(ids):
            raise ValueError("duplicate or orphan labels")
    projects = manifest["project_splits"]
    if Counter(projects.values()) != {"development": 2, "validation": 1, "test": 1}:
        raise ValueError("invalid project split")
    categories = {
        "exact_identifier": 3,
        "paraphrase": 3,
        "temporal_revision": 2,
        "missing_conflicting": 2,
        "unsupported_ambiguous": 2,
    }
    for project in projects:
        if Counter(q["category"] for q in queries if q["project"] == project) != categories:
            raise ValueError("invalid category denominators")
    for query, case in ((q, next(c for c in gold if c["id"] == q["id"])) for q in queries):
        if (
            query["project"] not in projects
            or case["project"] != query["project"]
            or query["request"]["project"] != query["project"]
        ):
            raise ValueError("query scope mismatch")
        if not query["text"] or query["execution_layer"] != "oracle-bound-structured-http":
            raise ValueError("invalid query contract")
        if case["http_status"] == 200:
            if not case["required_evidence"].get("governance") or not case["source_rows"]:
                raise ValueError("missing required evidence roles")
            if case["status"] in ("anomaly", "clear") and not case["required_evidence"].get(
                "observation"
            ):
                raise ValueError("missing order support")
            rows = {(r["artifact_id"], r["row"]) for r in case["source_rows"]}
            for role, refs in case["required_evidence"].items():
                for ref in refs:
                    if (
                        len(ref.get("content_hash", "")) != 64
                        or ref["role"] != role
                        or (ref["artifact_id"], ref["row"]) not in rows
                        or ref["location"] not in ("quantity", "authority")
                    ):
                        raise ValueError("orphan evidence label")
        elif (
            case["http_status"] != 422
            or case.get("code") != "invalid_request"
            or case["required_evidence"]
        ):
            raise ValueError("invalid rejection oracle")
    by_gold = {case["id"]: case for case in gold}
    for entry in qrels:
        expected = {
            json.dumps(ref, sort_keys=True)
            for refs in by_gold[entry["query_id"]]["required_evidence"].values()
            for ref in refs
        }
        actual = {
            json.dumps({k: v for k, v in ref.items() if k != "grade"}, sort_keys=True)
            for ref in entry["relevance"]
        }
        if actual != expected or any(ref["grade"] != 3 for ref in entry["relevance"]):
            raise ValueError("qrels disagree with evidence support")
    return {"manifest": manifest, "queries": queries, "gold": by_gold}


def score_response(status: int, response: dict[str, Any], gold: dict[str, Any]) -> list[str]:
    if not isinstance(response, dict):
        raise TypeError("response must be an object")
    evidence = response.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
        raise ValueError("evidence must be a list of objects")
    for name in ("evidence_by_role", "input_dispositions"):
        if not isinstance(response.get(name, {}), dict):
            raise TypeError("invalid response mapping")
    errors = []
    if status != gold["http_status"]:
        return ["http_status"]
    if status != 200:
        return [] if response.get("code") == gold["code"] else ["error_code"]
    for key in ("status", "reason"):
        if response.get(key) != gold[key]:
            errors.append(key)
    for key in ("required_quantity", "ordered_quantity"):
        actual = response.get(key)
        expected = gold[key]
        try:
            if (actual is None) != (expected is None) or (
                actual is not None and Decimal(str(actual)) != Decimal(str(expected))
            ):
                errors.append(key)
        except InvalidOperation:
            errors.append(key)
    evidence = response.get("evidence", [])
    for role, refs in gold["required_evidence"].items():
        for ref in refs:
            authority = ref["location"] == "authority"
            matches = [
                e
                for e in evidence
                if e.get("content_hash") == ref.get("content_hash")
                and e.get("artifact_id") == ref["artifact_id"] + ("-authority" if authority else "")
                and (
                    e.get("record_key") == str(ref["row"])
                    if authority
                    else e.get("row") == ref["row"]
                )
                and e.get("location_kind") == ("record" if authority else "tabular")
                and (
                    e.get("collection") == "records"
                    if authority
                    else e.get("sheet") == "BOM" and e.get("cells") == ["A", "B", "C", "D", "E"]
                )
            ]
            if not any(
                e["evidence_id"] in response.get("evidence_by_role", {}).get(role, [])
                for e in matches
            ):
                errors.append("required_evidence:" + role)
    expected_dispositions = gold.get("expected_input_dispositions")
    if expected_dispositions is not None and set(
        response.get("input_dispositions", {}).values()
    ) != set(expected_dispositions):
        errors.append("input_dispositions")
    return errors


def validate_source(
    source: dict[str, Any], ref: dict[str, Any], expected: dict[str, Any], project: str, item: str
) -> list[str]:
    """Check original content as well as the locator returned by the public source route."""
    if not isinstance(source, dict):
        raise TypeError("source must be an object")
    if source.get("evidence") != {k: v for k, v in ref.items() if k != "url"}:
        return ["source_resolution"]
    if ref["location_kind"] == "record":
        authority = source.get("authority")
        if not isinstance(authority, dict) or not isinstance(authority.get("document"), dict):
            return ["authority_source"]
        document = authority["document"]
        if (
            ref.get("collection") != "records"
            or document.get("project_id") != project
            or document.get("artifact_id") != expected["artifact_id"]
            or document.get("role") != expected["role"]
            or document.get("tenant_id") != "synthetic-tenant"
            or document.get("site_id") != "lab"
            or authority.get("record") != expected["authority_record"]
        ):
            return ["authority_source"]
    else:
        cells = source.get("cells")
        if (
            ref.get("sheet") != "BOM"
            or ref.get("cells") != ["A", "B", "C", "D", "E"]
            or not isinstance(cells, list)
            or len(cells) != 5
            or cells[0] != item
            or cells[2] != expected["quantity"]
            or cells[4] != "each"
        ):
            return ["original_quantity_source"]
    return []


def summarize(expected_ids: list[str], results: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {r["id"]: r for r in results}
    if len(by_id) != len(results) or set(by_id) - set(expected_ids):
        raise ValueError("duplicate or unexpected scored query")
    complete = [
        by_id.get(q, {"id": q, "outcome": "unknown", "errors": ["missing query result"]})
        for q in expected_ids
    ]
    counts = {
        name: sum(r["outcome"] == name for r in complete)
        for name in ("pass", "fail", "unknown", "not_applicable")
    }
    return {
        "counts": counts,
        "ready": counts["pass"] == len(expected_ids) and bool(expected_ids),
        "results": complete,
    }


def _fetch(url: str) -> tuple[int, dict[str, Any]]:
    try:
        with urlopen(url, timeout=20) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def evaluate(base_url: str, directory: Path = DATASET) -> dict[str, Any]:
    dataset = load_dataset(directory)
    results = []
    resolved = 0
    for query in dataset["queries"]:
        case = dataset["gold"][query["id"]]
        try:
            status, response = _fetch(
                base_url.rstrip("/") + "/api/corpus/investigate?" + urlencode(query["request"])
            )
            errors = score_response(status, response, case)
            if status == 200:
                expected_rows = {
                    (row["artifact_id"], row["row"]): row for row in case["source_rows"]
                }
                # Resolve every returned reference; inspect quantity cells and authority descriptors.
                for ref in response.get("evidence", []):
                    expected_url = "/api/corpus/source?" + urlencode(
                        {"project": query["project"], "evidence_id": ref["evidence_id"]}
                    )
                    if ref.get("url") != expected_url:
                        errors.append("source_url")
                        continue
                    source_status, source = _fetch(base_url.rstrip("/") + expected_url)
                    if source_status != 200:
                        errors.append("source_resolution")
                        continue
                    authority = ref["location_kind"] == "record"
                    artifact = (
                        ref["artifact_id"].removesuffix("-authority")
                        if authority
                        else ref["artifact_id"]
                    )
                    row_number = int(ref["record_key"]) if authority else ref["row"]
                    expected = expected_rows.get((artifact, row_number))
                    if expected is None:
                        errors.append("unexpected_source")
                        continue
                    errors.extend(
                        validate_source(
                            source, ref, expected, query["project"], query["request"]["item"]
                        )
                    )
                    resolved += 1
            result = {"id": query["id"], "outcome": "fail" if errors else "pass", "errors": errors}
        except (
            URLError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as error:
            result = {"id": query["id"], "outcome": "unknown", "errors": [type(error).__name__]}
        results.append(result | {"project": query["project"], "category": query["category"]})
    report = summarize([q["id"] for q in dataset["queries"]], results)
    report.update(
        {
            "schema_version": 1,
            "layer": "oracle-bound-structured-http",
            "agent_interpretation": "not_evaluated",
            "retrieval_quality": "not_evaluated",
            "dataset_manifest_sha256": sha256(
                (directory / "manifest.json").read_bytes()
            ).hexdigest(),
            "source_references_resolved": resolved,
        }
    )
    report["by_project"] = {
        project: dict(Counter(r["outcome"] for r in results if r["project"] == project))
        for project in dataset["manifest"]["project_splits"]
    }
    report["by_category"] = {
        category: dict(Counter(r["outcome"] for r in results if r["category"] == category))
        for category in sorted({q["category"] for q in dataset["queries"]})
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.base_url, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    raise SystemExit(0 if report["ready"] else 1)
