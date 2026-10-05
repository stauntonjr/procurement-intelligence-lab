"""Unit execution of shipped browser event wiring, distinct from browser acceptance."""

import shutil
import subprocess
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces.review_page import HTML


def test_review_page_uses_analyst_first_reconciliation_language() -> None:
    for text in (
        "Check procurement evidence",
        "Item to review",
        "Evidence available through",
        "Check for discrepancies",
        "Discrepancy assessment",
        "Source evidence",
        "Resolve or review",
        "Keep this item unresolved",
        "Assessment needs correction",
    ):
        assert text in HTML
    for text in (
        "Independent interview reference demo",
        "demo brief",
        "Investigate and draft",
        "Typed requests only",
        "Recent owned runs",
        "Selected persisted run",
        "Review finding",
        "Approve this finding",
        "Reject this finding",
    ):
        assert text not in HTML


@pytest.mark.parametrize("mode", ["success", "source-failure"])
def test_discovered_run_remains_recoverable_after_status_failure(tmp_path: Path, mode: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("optional Node renderer unit probe; real HTTP acceptance still runs")
    page = tmp_path / "review.html"
    page.write_text(HTML)
    result = subprocess.run(
        [node, str(Path(__file__).with_name("review_page_probe.cjs")), str(page), mode],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
