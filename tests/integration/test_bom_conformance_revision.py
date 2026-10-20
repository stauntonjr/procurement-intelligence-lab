from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_conformance_fixtures import conformance_checkout

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    return conformance_checkout(tmp_path / "checkout")


@pytest.mark.parametrize(
    "change",
    ["matching", "derived", "mismatch", "tracked_dirty", "untracked_dirty", "foreign_package"],
)
def test_conformance_cli_reports_only_verified_clean_checkout_revision(
    checkout: Path, tmp_path: Path, change: str
) -> None:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()
    declared = "0" * 40 if change == "mismatch" else revision
    if change == "tracked_dirty":
        with (checkout / "src/procurement_intelligence_lab/adapters/xlsx_structure.py").open(
            "a"
        ) as output:
            output.write("\n# Uncommitted source change\n")
    elif change == "untracked_dirty":
        (checkout / "untracked-source.py").write_text("# Untracked source\n")
    report = tmp_path / "report.json"
    command = [
        sys.executable,
        str(checkout / "tools/benchmark_bom_stages.py"),
        "--output",
        str(report),
    ]
    if change != "derived":
        command += ["--revision", declared]
    environment = {
        **os.environ,
        "PYTHONPATH": str((ROOT if change == "foreign_package" else checkout) / "src"),
    }
    result = subprocess.run(
        command, cwd=tmp_path, env=environment, capture_output=True, text=True, check=False
    )
    if change in {"matching", "derived"}:
        assert result.returncode == 0, result.stderr
        data = json.loads(report.read_text())
        assert data["passed"] is True and data["revision"] == revision
    else:
        assert result.returncode == 2, result.stdout
        assert not result.stdout and not report.exists()
        assert "conformance context" in result.stderr
