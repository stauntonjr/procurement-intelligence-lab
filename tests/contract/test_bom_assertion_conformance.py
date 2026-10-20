import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_conformance_fixtures import conformance_checkout

pytestmark = pytest.mark.contract


def test_nine_source_assertion_has_independent_hash_pinned_gold(tmp_path: Path) -> None:
    repo = conformance_checkout(tmp_path / "checkout")
    output = tmp_path / "assertion.json"
    result = subprocess.run(
        [sys.executable, "-m", "tools.benchmark_bom_assertions", "--output", str(output)],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": f"{repo / 'src'}:{repo}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["passed"] is True
    assert len(report["sources"]) == 9
    assert sum(x["assertions"]["count"] for x in report["sources"]) == 1608
    assert all(all(x["checks"].values()) for x in report["sources"])
    assert sum(x["mentions"]["count"] for x in report["sources"]) == 322
    assert report["inference_calls"] == 0


@pytest.mark.parametrize("change", ["source_hash", "gold", "revision", "dirty"])
def test_assertion_conformance_rejects_false_success(tmp_path: Path, change: str) -> None:
    repo = conformance_checkout(tmp_path / "checkout")
    manifest = json.loads((repo / "evals/extraction/bom-assertions-v1/manifest.json").read_text())
    manifest["sources"] = manifest["sources"][:1]
    if change == "source_hash":
        manifest["sources"][0]["sha256"] = "0" * 64
    elif change == "gold":
        manifest["sources"][0]["expected"]["sha256"] = "0" * 64
    elif change == "dirty":
        (repo / "changed.txt").write_text("uncommitted")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    output = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "tools.benchmark_bom_assertions",
        "--manifest",
        str(path),
        "--output",
        str(output),
    ]
    if change == "revision":
        command += ["--revision", "0" * 40]
    result = subprocess.run(
        command,
        cwd=repo,
        env={**os.environ, "PYTHONPATH": f"{repo / 'src'}:{repo}"},
        text=True,
        capture_output=True,
        check=False,
    )
    if change in {"revision", "dirty"}:
        assert result.returncode == 2 and not output.exists()
    else:
        assert result.returncode == 1
        assert json.loads(output.read_text())["passed"] is False
