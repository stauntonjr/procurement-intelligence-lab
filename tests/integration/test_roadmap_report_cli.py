"""Exercise the actual report admission command used after the hosted reviewer."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPORT = """## Current state
The compiler is delivered (Issue #135).
## Drift or conflicts
The runtime planner remains pending (ADR-022).
## Missing durable intake
No private chat access; no additional intake established.
## Recommended human decisions
Review runtime planning scope before scheduling it.
"""


@pytest.mark.integration
@pytest.mark.parametrize("case", ["valid", "missing", "malformed", "empty_sections", "quota"])
def test_report_cli_admits_only_complete_reports(tmp_path: Path, case: str) -> None:
    report = tmp_path / "response.json"
    output = tmp_path / "output"
    if case != "missing":
        values = {
            "valid": json.dumps({"response": REPORT}),
            "malformed": "not json",
            "empty_sections": json.dumps(
                {
                    "response": "## Current state\n## Drift or conflicts\n"
                    "## Missing durable intake\n## Recommended human decisions\n"
                }
            ),
            "quota": json.dumps({"error": {"code": 429}}),
        }
        report.write_text(values[case], encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.run_roadmap_review",
            "--report-file",
            str(report),
            "--github-output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if case == "valid" else 1), result.stderr
    admitted = output.read_text(encoding="utf-8")
    if case == "valid":
        assert REPORT in admitted
        assert "roadmap_error" not in admitted
    else:
        assert "roadmap_report" not in admitted
        assert "roadmap_error<<" in admitted
