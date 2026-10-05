"""Actual HTTP/process probes with controlled protocol, never real inference in CI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import run_g2_adversarial as evaluator
from tools.run_g2_adversarial import protocol_endpoint, run_case


@pytest.mark.parametrize(
    "case", ["tool_timeout", "expired_approval", "changed_snapshot", "review_crash_scope"]
)
def test_installed_public_faults_and_exact_crash_recovery(tmp_path: Path, case: str) -> None:
    with protocol_endpoint("valid") as (endpoint, calls):
        row = run_case(case, sys.executable, tmp_path, endpoint, kind="controlled_protocol")
    assert row["outcome"] == "pass", row
    assert row["attempt_complete"] is True
    assert row["terminal_calls"] == 1
    assert row["real_qwen_calls"] == 0
    assert row["controlled_protocol_calls"] == calls[0] == 1
    assert row["saved_count"] == int(case == "review_crash_scope")
    if case == "tool_timeout":
        assert row["tool_failures"] == 1
        assert row["observations"]["ask"]["code"] == "pil.transient.agent_tool_timeout"
    if case == "review_crash_scope":
        assert row["observations"]["crash_exit"] == 86
        assert row["observations"]["saved_identity_preserved"] is True


def test_actual_cli_protocol_probe_retains_full_denominator(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "tools.run_g2_adversarial",
        "--protocol-only",
        "--python",
        sys.executable,
        "--workspace",
        str(tmp_path / "workspace"),
        "--output",
        str(output),
    ]
    done = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    report = json.loads(output.read_text())
    assert report["acceptance"] == "protocol_probe_passed"
    assert report["summary"]["counts"] == {"pass": 4, "fail": 0, "unknown": 0, "not_applicable": 5}
    assert report["summary"]["real_qwen_calls"] == 0
    assert report["summary"]["controlled_protocol_calls"] == 3
    assert "PRIVATE_INJECTED_REASONING" not in json.dumps(report)
    assert "Authorization" not in json.dumps(report)
    again = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    assert again.returncode != 0


def test_failed_guard_still_reports_actual_call_and_tool_attempts(tmp_path: Path) -> None:
    with protocol_endpoint("valid") as (endpoint, calls):
        row = run_case(
            "unsupported", sys.executable, tmp_path, endpoint, kind="controlled_protocol"
        )
    assert row["outcome"] == "fail"
    assert row["attempt_complete"] is True
    assert row["terminal_calls"] == row["controlled_protocol_calls"] == calls[0] == 1
    assert row["real_qwen_calls"] == 0
    assert row["tool_starts"] == 2
    assert row["saved_count"] == 0


@pytest.mark.parametrize(
    ("damage", "expected"),
    [
        ("empty", "unknown"),
        ("partial", "unknown"),
        ("foreign", "fail"),
        ("missing_run", "unknown"),
        ("foreign_receipt", "fail"),
    ],
)
def test_missing_or_foreign_audit_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str, expected: str
) -> None:
    original = evaluator.journal

    def damaged(directory: Path):
        audit = original(directory)
        if damage == "empty":
            audit["events"] = []
        elif damage == "partial":
            audit["events"] = [e for e in audit["events"] if e["kind"] != "tool_succeeded"]
        elif damage == "foreign" and audit["events"]:
            audit["events"][-1]["run_id"] = "foreign"
        elif damage == "missing_run":
            audit["runs"] = []
        elif damage == "foreign_receipt" and audit.get("receipts"):
            audit["receipts"][0]["run_id"] = "foreign"
        return audit

    monkeypatch.setattr(evaluator, "journal", damaged)
    with protocol_endpoint("valid") as (endpoint, calls):
        row = run_case(
            "expired_approval", sys.executable, tmp_path, endpoint, kind="controlled_protocol"
        )
    assert row["outcome"] == expected, row
    assert row["evidence_outcome"] == expected
    assert row["attempt_complete"] is True
    assert row["controlled_protocol_calls"] == calls[0] == 1
    assert row["saved_count"] == 0
