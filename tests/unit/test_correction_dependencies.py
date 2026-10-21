from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ApprovedCorrectionRef,
    ArchivedClaimRef,
    DependencyManifest,
    DependencySnapshot,
)
from procurement_intelligence_lab.platform.semantics.errors import DependencyContractError
from tests.unit.test_dependencies import AT, SCOPE, claim, manifest


def correction():
    return ApprovedCorrectionRef(
        ArchivedClaimRef("snapshot", "source"), "task", "a" * 64, "decision", "correction"
    )


def test_correction_is_data_root():
    source = ArchivedClaimRef("snapshot", "source")
    c = correction()
    graph = DependencyManifest(
        SCOPE,
        "reviewed",
        tuple(sorted((source, c), key=lambda r: r.reference_id)),
        (claim("query", "row"), claim("row", "source", "correction")),
    )
    assert graph.impact("correction", 2).affected == (("query", 2), ("row", 1))
    assert graph.impact("source", 1).frontier == ("query",)
    assert bootstrap.archive_codec().loads(bootstrap.archive_codec().dumps(graph)) == graph
    assert c.snapshot_id == "snapshot" and source.reference_id == "source"
    assert graph.impact("correction", 2).global_completeness == "not_evaluated"


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "untyped"},
        {"task_digest": "wrong"},
        {"task_id": ""},
        {"decision_id": "bad\ud800"},
        {"correction_id": " "},
    ],
)
def test_root_variants_require_exact_types(changes: dict[str, Any]):
    with pytest.raises(DependencyContractError):
        replace(correction(), **changes)


def test_missing_original_root_rejected():
    with pytest.raises(DependencyContractError):
        DependencyManifest(SCOPE, "request", (correction(),), ())


def test_cross_variant_id_collision_rejected():
    with pytest.raises(DependencyContractError):
        DependencyManifest(
            SCOPE,
            "request",
            (replace(correction(), correction_id="source"), ArchivedClaimRef("snapshot", "source")),
            (),
        )


def test_untyped_root_and_reordered_roots_are_rejected():
    with pytest.raises(DependencyContractError):
        DependencyManifest(SCOPE, "request", (cast(Any, "untyped"),), ())
    with pytest.raises(DependencyContractError):
        DependencyManifest(
            SCOPE, "request", (ArchivedClaimRef("snapshot", "source"), correction()), ()
        )


def test_old_snapshot_wire_is_identical():
    # Captured from main a26d615 before any runtime edit.
    # SHA256 below hashes the exact codec string, without the fixture's final newline.
    from hashlib import sha256

    raw = Path("tests/fixtures/dependency-archive-only-v1.json").read_text().rstrip("\n")
    codec = bootstrap.archive_codec()
    assert codec.dumps(DependencySnapshot(manifest(claim("a", "source")), "recorder", AT)) == raw
    assert codec.dumps(codec.loads(raw)) == raw
    assert (
        sha256(raw.encode()).hexdigest()
        == "37753a6dd1cc1ec0c65587ba1adf147ca6b437ae2953613588ee23fb3bf0508e"
    )
