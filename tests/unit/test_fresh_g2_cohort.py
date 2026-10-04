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


@pytest.mark.parametrize("mutation", ["category", "date", "item", "extra_request"])
def test_freshness_cannot_change_inherited_query_metadata(tmp_path: Path, mutation: str) -> None:
    manifest, frozen = fixture(tmp_path / "dataset")
    path = manifest.parent / "queries.json"
    data = json.loads(path.read_text())
    target = next(q for q in data["queries"] if q["id"] == "cinder-match")
    if mutation == "category":
        other = next(q for q in data["queries"] if q["id"] == "cinder-before-boundary")
        target["category"], other["category"] = other["category"], target["category"]
    elif mutation == "date":
        target["request"]["as_of"] = "2026-10-02T00:00:00+00:00"
    elif mutation == "item":
        target["request"]["item"] = "NIC-C1"
    else:
        target["request"]["operation"] = "approve"
    path.write_text(json.dumps(data))
    digest = sha256(path.read_bytes()).hexdigest()
    frozen["queries_sha256"] = digest
    meta_path = manifest.parent / "manifest.json"
    meta = json.loads(meta_path.read_text())
    meta["hashes"]["queries.json"] = digest
    meta_path.write_text(json.dumps(meta))
    manifest.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="metadata"):
        load_pilot(manifest.parent, manifest)


def upgrade_v3(manifest: Path, frozen: dict[str, Any]) -> None:
    frozen["schema_version"] = 3
    paths = PRIOR_FILES + (
        "evals/procurement_corpus/fresh-language-v2/queries.json",
        "evals/operational_agents/cutoff-development-v1.json",
    )
    frozen["freshness"]["prior_question_files"] = [
        {"path": p, "sha256": sha256((ROOT / p).read_bytes()).hexdigest()} for p in paths
    ]
    manifest.write_text(json.dumps(frozen))


def test_v3_lineage_preserves_historical_v2_and_accepts_fresh_wording(tmp_path: Path) -> None:
    manifest, frozen = fixture(tmp_path / "dataset")
    validate_fresh(manifest.parent, manifest, VERSIONS)
    upgrade_v3(manifest, frozen)
    validate_fresh(manifest.parent, manifest, VERSIONS)
    assert len(load_pilot(manifest.parent, manifest)) == 48


@pytest.mark.parametrize("mutation", ["omit_retired", "omit_controls", "changed_hash"])
def test_v3_requires_complete_current_question_history(tmp_path: Path, mutation: str) -> None:
    manifest, frozen = fixture(tmp_path / "dataset")
    upgrade_v3(manifest, frozen)
    history = frozen["freshness"]["prior_question_files"]
    if mutation == "changed_hash":
        history[-1]["sha256"] = "0" * 64
        reason = "lineage changed"
    else:
        del history[-2 if mutation == "omit_retired" else -1]
        reason = "complete prior-question lineage"
    manifest.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match=reason):
        validate_fresh(manifest.parent, manifest, VERSIONS)


@pytest.mark.parametrize("source", ["retired", "controls"])
def test_v3_rejects_inspected_cohort_and_cutoff_control_replay(tmp_path: Path, source: str) -> None:
    manifest, frozen = fixture(tmp_path / "dataset")
    upgrade_v3(manifest, frozen)
    if source == "retired":
        retired = json.loads(
            (ROOT / "evals/procurement_corpus/fresh-language-v2/queries.json").read_text()
        )
        prior = next(q for q in retired["queries"] if q["id"] == "cinder-before-boundary")
        query_id, text = prior["id"], prior["text"]
    else:
        controls = json.loads(
            (ROOT / "evals/operational_agents/cutoff-development-v1.json").read_text()
        )
        prior = next(q for q in controls["cases"] if q["id"] == "cutoff-matching")
        query_id, text = "atlas-mismatch", prior["question"]
    query_path = manifest.parent / "queries.json"
    queries = json.loads(query_path.read_text())
    query = next(q for q in queries["queries"] if q["id"] == query_id)
    query["text"] = "  " + text.upper() + "  "
    raw = json.dumps(queries).encode()
    query_path.write_bytes(raw)
    frozen["queries_sha256"] = sha256(raw).hexdigest()
    meta_path = manifest.parent / "manifest.json"
    meta = json.loads(meta_path.read_text())
    meta["hashes"]["queries.json"] = sha256(raw).hexdigest()
    meta_path.write_text(json.dumps(meta))
    author_path = manifest.parent / "independent-language-author.json"
    author = json.loads(author_path.read_text())
    for row in author["records"]:
        if row["id"] == query_id:
            row["text"] = query["text"]
    author_path.write_text(json.dumps(author))
    frozen["freshness"]["heldout_author_sha256"] = sha256(author_path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="old or duplicate wording"):
        validate_fresh(manifest.parent, manifest, VERSIONS)
