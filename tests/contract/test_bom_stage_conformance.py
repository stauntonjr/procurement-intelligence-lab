import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_conformance_fixtures import conformance_checkout
from tools.benchmark_bom_stages import DEFAULT_MANIFEST

pytestmark = pytest.mark.contract


def _report(tmp_path: Path, manifest: Path | None = None) -> dict[str, object]:
    repo = conformance_checkout(tmp_path / "checkout")
    output = tmp_path / "report.json"
    command = [sys.executable, str(repo / "tools/benchmark_bom_stages.py"), "--output", str(output)]
    if manifest is not None:
        command += ["--manifest", str(manifest)]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(repo / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in {0, 1}, result.stderr
    return json.loads(output.read_text())


def test_hash_pinned_bom_conformance_matches_each_layer(tmp_path: Path) -> None:
    report = _report(tmp_path)
    assert report["passed"] is True
    sources = json.loads(json.dumps(report["sources"]))
    assert len(sources) == 9
    assert all(
        set(record["checks"]) == {"rows", "cells", "fields", "field_evidence", "evidence_identity"}
        and all(record["checks"].values())
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
    report = _report(tmp_path, path)
    assert report["passed"] is False
    assert report["sources"] == [
        {
            "path": manifest["sources"][0]["path"],
            "outcome": "failed",
            "failure": "source_hash_mismatch",
        }
    ]
