"""Evaluator-only provenance for unseen wording over already inspected source data."""

import json
import re
import unicodedata
from hashlib import sha256
from pathlib import Path
from typing import Any

from tools.evaluate_procurement_corpus import ROOT, load_dataset

PRIOR_FILES = (
    "evals/procurement_corpus/v1/queries.json",
    "evals/operational_agents/intent-development-v1.json",
    "evals/operational_agents/local-qwen-walkthrough-v1.json",
    "evals/operational_agents/browser-walkthrough-v1.json",
    "evals/operational_agents/original-showcase-browser-v1.json",
)


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def questions(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("question", "text") and isinstance(item, str):
                found.add(normalized(item))
            else:
                found.update(questions(item))
    elif isinstance(value, list):
        for item in value:
            found.update(questions(item))
    return found


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def validate_fresh(dataset: Path, manifest: Path, versions: dict[str, str] | None = None) -> None:
    """Verify closed authorship/lineage claims; optional versions fence actual inference."""
    try:
        _validate(dataset, manifest, versions)
    except (KeyError, TypeError, OSError) as error:
        raise ValueError("invalid fresh-language provenance") from error


def _validate(dataset: Path, manifest: Path, versions: dict[str, str] | None) -> None:
    frozen = json.loads(manifest.read_bytes())
    _require(
        set(frozen)
        == {
            "schema_version",
            "queries_sha256",
            "contract",
            "cases",
            "evaluation_use",
            "limits",
            "freshness",
        },
        "closed fresh manifest required",
    )
    _require(
        type(frozen["schema_version"]) is int and frozen["schema_version"] == 2,
        "fresh manifest version required",
    )
    _require(
        frozen["evaluation_use"] == "fresh_language_holdout"
        and bool(frozen["limits"])
        and isinstance(frozen["limits"], str),
        "bounded language-only claim required",
    )
    data = load_dataset(dataset)
    old = load_dataset(ROOT / "evals/procurement_corpus/v1")
    inherited = {q["id"]: q for q in old["queries"]}
    for query in data["queries"]:
        original = inherited.get(query["id"], {})
        _require(
            {k: v for k, v in query.items() if k != "text"}
            == {k: v for k, v in original.items() if k != "text"},
            "inherited query metadata changed; only wording may change",
        )
    _require(
        data["manifest"]["project_splits"] == old["manifest"]["project_splits"],
        "source splits cannot be relabeled",
    )
    for name in ("pilot-gold.json", "qrels.json"):
        _require(
            (dataset / name).read_bytes()
            == (ROOT / "evals/procurement_corpus/v1" / name).read_bytes(),
            "existing source oracle required",
        )
    _require(
        frozen["queries_sha256"] == sha256((dataset / "queries.json").read_bytes()).hexdigest(),
        "frozen query hash mismatch",
    )
    fresh = frozen["freshness"]
    _require(
        set(fresh)
        == {
            "runtime_git_revision",
            "runtime_versions",
            "source_reuse",
            "heldout_author_file",
            "heldout_author_sha256",
            "prior_question_files",
        },
        "closed freshness metadata required",
    )
    _require(
        bool(re.fullmatch(r"[0-9a-f]{40}", fresh["runtime_git_revision"])),
        "runtime revision required",
    )
    bound = fresh["runtime_versions"]
    _require(
        set(bound) == {"provider", "model", "prompt", "tool_schema", "fixture", "application"}
        and all(isinstance(v, str) and v for v in bound.values()),
        "closed runtime bindings required",
    )
    _require(
        bound["fixture"] == data["manifest"]["runtime_manifest_sha256"],
        "source snapshot binding required",
    )
    _require(versions is None or bound == versions, "runtime changed after language freeze")
    _require(
        fresh["source_reuse"] == "previously_inspected_source_scenarios",
        "cannot claim unseen source projects",
    )
    prior = fresh["prior_question_files"]
    _require(
        len(prior) == len(PRIOR_FILES) and {p["path"] for p in prior} == set(PRIOR_FILES),
        "complete prior-question lineage required",
    )
    known: set[str] = set()
    for item in prior:
        _require(set(item) == {"path", "sha256"}, "closed prior provenance required")
        path = ROOT / item["path"]
        _require(
            not path.is_symlink() and sha256(path.read_bytes()).hexdigest() == item["sha256"],
            "prior question lineage changed",
        )
        known.update(questions(json.loads(path.read_bytes())))
    qs = data["queries"]
    texts = [normalized(q["text"]) for q in qs]
    _require(
        len(set(texts)) == len(qs) and not set(texts) & known,
        "old or duplicate wording cannot be fresh",
    )
    _require(
        fresh["heldout_author_file"] == "independent-language-author.json",
        "fixed evaluator-only author file required",
    )
    author_path = dataset / fresh["heldout_author_file"]
    _require(
        not author_path.is_symlink()
        and sha256(author_path.read_bytes()).hexdigest() == fresh["heldout_author_sha256"],
        "author record hash mismatch",
    )
    author = json.loads(author_path.read_bytes())
    _require(
        set(author)
        == {"schema_version", "author", "author_model", "authoring_context", "excluded", "records"},
        "closed author record required",
    )
    _require(
        type(author["schema_version"]) is int
        and author["schema_version"] == 1
        and isinstance(author["author"], str)
        and bool(author["author"])
        and isinstance(author["author_model"], str)
        and bool(author["author_model"]),
        "identified independent author required",
    )
    _require(
        author["authoring_context"] == "independent_fresh_context"
        and author["excluded"] == ["old_questions", "model_outputs", "runtime_prompt"],
        "independent author context required",
    )
    heldout = {
        q["id"]: q
        for q in qs
        if data["manifest"]["project_splits"][q["project"]] in ("validation", "test")
    }
    records = author["records"]
    _require(
        len(records) == 24
        and len({r["id"] for r in records}) == 24
        and {r["id"] for r in records} == set(heldout),
        "exactly24heldout author records required",
    )
    expected = {r["id"]: r["expected"] for r in frozen["cases"]}
    _require(
        len(frozen["cases"]) == 48
        and len(expected) == 48
        and set(expected) == {q["id"] for q in qs},
        "complete interpretation labels required",
    )
    for record in records:
        _require(
            set(record) == {"id", "text", "expected"}
            and record["text"] == heldout[record["id"]]["text"]
            and record["expected"] == expected[record["id"]]
            and record["expected"] in ("investigate", "clarify", "unsupported"),
            "authored question/label binding mismatch",
        )
