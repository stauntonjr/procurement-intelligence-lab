"""Public evaluator CLI retains full denominators when startup transport fails."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import run_g2_pilot


def test_public_runner_finalizes_startup_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.json"
    database = tmp_path / "runs.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_g2_pilot",
            "--run-live",
            "--python",
            sys.executable,
            "--database",
            str(database),
            "--output",
            str(output),
        ],
    )

    def unavailable(*_: Any, **__: Any) -> Any:
        raise TimeoutError("model discovery timeout")

    monkeypatch.setattr(run_g2_pilot, "urlopen", unavailable)
    assert run_g2_pilot.main() == 1
    report = json.loads(output.read_text())
    assert report["acceptance"] == "not_ready"
    assert report["interpretation"]["counts"] == {
        "pass": 0,
        "fail": 0,
        "unknown": 48,
        "not_applicable": 0,
    }
    assert len(report["attempt_audit"]) == 48
    assert all(row["model_calls"] is None for row in report["attempt_audit"])
    assert report["operation_errors"] == ["TimeoutError"]


def test_public_runner_refuses_to_overwrite_prior_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "prior.json"
    output.write_text("retained")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_g2_pilot",
            "--run-live",
            "--python",
            sys.executable,
            "--database",
            str(tmp_path / "runs.db"),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(ValueError, match="fresh database/output"):
        run_g2_pilot.main()
    assert output.read_text() == "retained"
