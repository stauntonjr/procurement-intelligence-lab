import json
from pathlib import Path

import pytest

from tools.benchmark_bom_stages import DEFAULT_MANIFEST, benchmark

pytestmark = pytest.mark.contract


def test_hash_pinned_bom_conformance_matches_each_layer() -> None:
    report = benchmark(DEFAULT_MANIFEST, "contract-test")
    assert report["passed"] is True
    sources = json.loads(json.dumps(report["sources"]))
    assert len(sources) == 9
    assert all(
        set(record["checks"]) == {"rows", "cells", "fields"} and all(record["checks"].values())
        for record in sources
    )
    assert sum(record["layers"]["fields"]["count"] for record in sources) == 1608
    assert report["inference_calls"] == 0 and report["compute_cost_usd"] is None


def test_conformance_rejects_wrong_source_hash_before_reporting_recovery(tmp_path: Path) -> None:
    manifest = json.loads(DEFAULT_MANIFEST.read_text())
    manifest["sources"] = manifest["sources"][:1]
    manifest["sources"][0]["sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    report = benchmark(path, "contract-test")
    assert report["passed"] is False
    assert report["sources"] == [
        {
            "path": manifest["sources"][0]["path"],
            "outcome": "failed",
            "failure": "source_hash_mismatch",
        }
    ]
