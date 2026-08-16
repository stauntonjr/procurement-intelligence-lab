import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from tools import run_roadmap_review

VALID_REPORT = """## Current state
Current evidence.
## Drift or conflicts
No confirmed drift.
## Missing durable intake
None found.
## Recommended human decisions
No decision required.
"""


def test_parse_report_requires_the_complete_advisory_contract() -> None:
    assert run_roadmap_review.parse_report(json.dumps({"response": VALID_REPORT})) == VALID_REPORT


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("", "valid JSON"),
        ("not-json", "valid JSON"),
        ("[]", "JSON object"),
        ('{"response":""}', "non-empty response"),
        ('{"response":"## Current state\\nincomplete"}', "exactly the required headings"),
    ],
)
def test_parse_report_rejects_missing_or_malformed_reviews(stdout: str, message: str) -> None:
    with pytest.raises(run_roadmap_review.RoadmapReviewError, match=message):
        run_roadmap_review.parse_report(stdout)


def test_run_review_writes_valid_report_output(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Review the roadmap.", encoding="utf-8")
    output = tmp_path / "github-output"

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[0] == [
            "gemini",
            "--yolo",
            "--prompt",
            "Review the roadmap.",
            "--output-format",
            "json",
        ]
        assert kwargs == {
            "cwd": run_roadmap_review.ROOT,
            "check": False,
            "capture_output": True,
            "text": True,
        }
        return subprocess.CompletedProcess([], 0, json.dumps({"response": VALID_REPORT}), "")

    monkeypatch.setattr(run_roadmap_review.subprocess, "run", fake_run)

    assert run_roadmap_review.run_review(Path("gemini"), prompt, output) == 0
    contents = output.read_text(encoding="utf-8")
    assert "roadmap_report<<" in contents
    assert VALID_REPORT in contents
    assert "roadmap_error" not in contents


def test_run_review_fails_when_cli_does_not_produce_a_real_report(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Review the roadmap.", encoding="utf-8")
    output = tmp_path / "github-output"

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, '{"response":"quota exhausted"}', "")

    monkeypatch.setattr(run_roadmap_review.subprocess, "run", fake_run)

    assert run_roadmap_review.run_review(Path("gemini"), prompt, output) == 1
    contents = output.read_text(encoding="utf-8")
    assert "roadmap_error<<" in contents
    assert "exactly the required headings" in contents


def test_run_review_fails_closed_when_prompt_is_missing(tmp_path: Path) -> None:
    output = tmp_path / "github-output"

    assert run_roadmap_review.run_review(Path("gemini"), tmp_path / "missing.md", output) == 1
    assert "roadmap_error<<" in output.read_text(encoding="utf-8")


def test_workflow_uses_the_lockfile_pinned_direct_cli() -> None:
    workflow = Path(".github/workflows/roadmap-stewardship.yml").read_text(encoding="utf-8")
    allowlist = json.loads(Path(".github/actions-allowlist.json").read_text(encoding="utf-8"))
    package = json.loads(Path(".github/roadmap-steward/package.json").read_text(encoding="utf-8"))
    lock = json.loads(Path(".github/roadmap-steward/package-lock.json").read_text(encoding="utf-8"))
    settings = json.loads(Path(".github/roadmap-steward/settings.json").read_text(encoding="utf-8"))

    assert "google-github-actions/run-gemini-cli" not in workflow
    assert "continue-on-error" not in workflow
    assert "npm ci --ignore-scripts --no-audit --no-fund" in workflow
    assert "python -m tools.run_roadmap_review" in workflow
    assert "google-github-actions/run-gemini-cli" not in {
        item["repository"] for item in allowlist["allowed_actions"]
    }
    assert package["dependencies"]["@google/gemini-cli"] == "0.55.1"
    assert lock["packages"][""]["dependencies"]["@google/gemini-cli"] == "0.55.1"
    cli = lock["packages"]["node_modules/@google/gemini-cli"]
    assert cli["version"] == "0.55.1"
    assert cli["integrity"].startswith("sha512-")
    assert settings["tools"]["core"] == ["read_file"]
