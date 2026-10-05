"""Execute shipped live-page wiring; does not establish browser acceptance."""

import shutil
import subprocess
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces.review_page import live_html


def test_live_page_exact_review_and_clarification_wiring(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for JavaScript wiring check; no browser acceptance")
    html = tmp_path / "live.html"
    html.write_text(live_html())
    result = subprocess.run(
        [node, str(Path(__file__).with_name("live_review_page_probe.cjs")), str(html)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
