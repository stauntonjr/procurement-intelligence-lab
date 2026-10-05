"""Deterministic shipped JavaScript defect oracles; real browser acceptance is separate."""

import shutil
import subprocess
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces.review_page import HTML, live_html


@pytest.mark.parametrize("mode", ["fixture", "live"])
@pytest.mark.parametrize("defect", ["retain", "malformed", "json", "lock"])
def test_shipped_page_recovery_oracle(tmp_path: Path, mode: str, defect: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for public JavaScript challenge oracle")
    page = tmp_path / "page.html"
    page.write_text(HTML if mode == "fixture" else live_html())
    done = subprocess.run(
        [
            node,
            str(Path(__file__).with_name("review_page_recovery_probe.cjs")),
            str(page),
            defect,
            mode,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
