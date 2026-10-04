"""Unseen-language claims must bind author records, lineage and frozen runtime."""

import json
import shutil
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from tools.fresh_g2_cohort import PRIOR_FILES, validate_fresh
from tools.g2_pilot_scoring import load_pilot

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {
    "provider": "local-vllm",
    "model": "qwen",
    "prompt": "p",
    "tool_schema": "t",
    "fixture": "a92add68a76dca7bf0818bc073b0d8f127c0a6b28544c22f62b90d143fa4bd64",
    "application": "a",
}


def fixture(directory: Path) -> tuple[Path, dict[str, Any]]:
    shutil.copytree(ROOT / "evals/procurement_corpus/v1", directory)
    queries = json.loads((directory / "queries.json").read_text())
    for n, query in enumerate(queries["queries"]):
        query["text"] = f"Independently phrased request number {n} for {query['request']['item']}."
    raw = (json.dumps(queries, indent=2) + "\n").encode()
    (directory / "queries.json").write_bytes(raw)
    data = json.loads((directory / "manifest.json").read_text())
    data["hashes"]["queries.json"] = sha256(raw).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(data))
    frozen = json.loads((ROOT / "evals/operational_agents/g2-pilot-v1.json").read_text())
    expected = {r["id"]: r["expected"] for r in frozen["cases"]}
    authored = {
        "schema_version": 1,
        "author": "independent-reviewer",
        "author_model": "review-model",
        "authoring_context": "independent_fresh_context",
        "excluded": ["old_questions", "model_outputs", "runtime_prompt"],
        "records": [
            {"id": q["id"], "text": q["text"], "expected": expected[q["id"]]}
            for q in queries["queries"]
            if q["project"] in ("cinder", "delta")
        ],
    }
    author = directory / "independent-language-author.json"
    author.write_text(json.dumps(authored))
    frozen.update(
        schema_version=2,
        queries_sha256=sha256(raw).hexdigest(),
        evaluation_use="fresh_language_holdout",
        limits="Known sources; new language only.",
        freshness={
            "runtime_git_revision": "55bac5c598d420faed2767a1afd1018c1df38f5c",
            "runtime_versions": deepcopy(VERSIONS),
            "source_reuse": "previously_inspected_source_scenarios",
            "heldout_author_file": author.name,
            "heldout_author_sha256": sha256(author.read_bytes()).hexdigest(),
            "prior_question_files": [
                {"path": p, "sha256": sha256((ROOT / p).read_bytes()).hexdigest()}
                for p in PRIOR_FILES
            ],
        },
    )
    manifest = directory / "language-v2.json"
    manifest.write_text(json.dumps(frozen))
    return manifest, frozen


def test_fresh_selected_cohort_binds_24_independent_cases(tmp_path: Path) -> None:
    manifest, _ = fixture(tmp_path / "dataset")
    validate_fresh(manifest.parent, manifest, VERSIONS)
    cases = load_pilot(manifest.parent, manifest)
    assert len(cases) == 48
    assert len([c for c in cases if c["split"] in ("validation", "test")]) == 24


@pytest.mark.parametrize(
    "mutation",
    [
        "versions",
        "source",
        "author_hash",
        "author_path",
        "old_hash",
        "extra",
        "replay",
        "duplicate",
        "label",
        "author_row",
        "author_context",
    ],
)
def test_fresh_claim_rejects_drift_and_false_authorship(tmp_path: Path, mutation: str) -> None:
    manifest, frozen = fixture(tmp_path / "dataset")
    fresh = frozen["freshness"]
    if mutation == "versions":
        fresh["runtime_versions"]["prompt"] = "changed"
    elif mutation == "source":
        fresh["source_reuse"] = "fresh_projects"
    elif mutation == "author_hash":
        fresh["heldout_author_sha256"] = "0" * 64
    elif mutation == "author_path":
        fresh["heldout_author_file"] = "../outside.json"
    elif mutation == "old_hash":
        fresh["prior_question_files"][0]["sha256"] = "0" * 64
    elif mutation == "extra":
        frozen["unverified_claim"] = "fresh"
    else:
        author = manifest.parent / fresh["heldout_author_file"]
        data = json.loads(author.read_text())
        queries = json.loads((manifest.parent / "queries.json").read_text())
        if mutation in ("replay", "duplicate"):
            q = next(q for q in queries["queries"] if q["id"] == data["records"][0]["id"])
            text = (
                "  COMPARE gpu-a WITH THE GOVERNING REQUIREMENT.  "
                if mutation == "replay"
                else queries["queries"][0]["text"]
            )
            q["text"] = data["records"][0]["text"] = text
            raw = json.dumps(queries).encode()
            (manifest.parent / "queries.json").write_bytes(raw)
            frozen["queries_sha256"] = sha256(raw).hexdigest()
            meta = json.loads((manifest.parent / "manifest.json").read_text())
            meta["hashes"]["queries.json"] = sha256(raw).hexdigest()
            (manifest.parent / "manifest.json").write_text(json.dumps(meta))
        elif mutation == "label":
            data["records"][0]["expected"] = "unsupported"
        elif mutation == "author_row":
            data["records"][0] = data["records"][1]
        else:
            data["authoring_context"] = "runtime_author"
        author.write_text(json.dumps(data))
        fresh["heldout_author_sha256"] = sha256(author.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(frozen))
    with pytest.raises(ValueError):
        validate_fresh(manifest.parent, manifest, VERSIONS)
