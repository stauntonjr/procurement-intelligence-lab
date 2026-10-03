"""Public fixture workflow across real processes, including a crash after save."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def invoke(
    path: Path, operation: str, *args: str, project: str = "atlas", crash: bool = False
) -> subprocess.CompletedProcess[str]:
    argv = ["--database", str(path), operation, "--project", project, *args]
    command = [sys.executable, "-m", "procurement_intelligence_lab.interfaces.workflow", *argv]
    if crash:
        script = """
import os,sys
from procurement_intelligence_lab.application.exact_brief_review import BriefReviewService
from procurement_intelligence_lab.interfaces.workflow import main
original = BriefReviewService.save
def save(self, *args, **kwargs):
    original(self, *args, **kwargs)
    os._exit(86)
BriefReviewService.save = save
sys.argv = ['workflow'] + sys.argv[1:]
raise SystemExit(main())
"""
        command = [sys.executable, "-c", script, *argv]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def start(path: Path, item: str = "GPU-A") -> dict[str, Any]:
    p = invoke(path, "start", "--item", item, "--as-of", "2026-10-01T00:00:00Z")
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(p.stdout)


def test_process_restart_crash_recovery_duplicate_save_and_allowlist(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    view = start(path)
    assert view["execution_kind"] == "fixture" and view["status"] == "awaiting_review"
    assert set(view) == {"run_id", "execution_kind", "status", "brief", "saved"}
    brief = view["brief"]
    arguments = [
        "--run-id",
        view["run_id"],
        "--brief-id",
        brief["brief_id"],
        "--digest",
        brief["digest"],
        "--decision",
        "approve",
    ]
    failed = invoke(path, "review", *arguments, crash=True)
    assert failed.returncode == 86
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM brief_receipts").fetchone()[0] == 1
    recovered = invoke(path, "review", *arguments)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    payload = json.loads(recovered.stdout)
    assert payload["status"] == "completed" and payload["saved"]["digest"] == brief["digest"]
    again = invoke(path, "review", *arguments)
    assert json.loads(again.stdout) == payload
    assert json.loads(invoke(path, "status", "--run-id", view["run_id"]).stdout) == payload
    assert "permissions" not in recovered.stdout and "checkpoint" not in recovered.stdout


def test_public_foreign_scope_and_no_checkpoint_fork(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    view = start(path)
    foreign = invoke(path, "status", "--run-id", view["run_id"], project="delta")
    assert foreign.returncode == 1 and json.loads(foreign.stdout)["category"] == "input"
    fork = invoke(path, "status", "--run-id", view["run_id"], "--checkpoint-id", "old")
    assert fork.returncode != 0
    approved = invoke(path, "review", "--run-id", view["run_id"], "--approved", "true")
    assert approved.returncode != 0


def test_real_parser_in_process_preserves_unknown_and_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from procurement_intelligence_lab.interfaces.workflow import main

    path = tmp_path / "runs.db"

    def call(operation: str, *args: str, project: str = "atlas") -> tuple[int, dict[str, Any]]:
        monkeypatch.setattr(
            sys,
            "argv",
            ["workflow", "--database", str(path), operation, "--project", project, *args],
        )
        code = main()
        return code, json.loads(capsys.readouterr().out)

    code, view = call("start", "--item", "GPU-C", "--as-of", "2026-10-01T00:00:00Z")
    assert code == 0
    facts = json.loads(view["brief"]["content_json"])
    assert facts["required_quantity"] is None and facts["ordered_quantity"] is None
    assert facts["status"] == "not_assessed"
    assert call("recover", "--run-id", view["run_id"]) == (0, view)
    assert call("status", "--run-id", view["run_id"]) == (0, view)
    brief = view["brief"]
    code, rejected = call(
        "review",
        "--run-id",
        view["run_id"],
        "--brief-id",
        brief["brief_id"],
        "--digest",
        brief["digest"],
        "--decision",
        "reject",
    )
    assert code == 0 and rejected["status"] == "rejected" and rejected["saved"] is None
    assert call("status", "--run-id", view["run_id"], project="delta")[0] == 1
    assert (
        call("status", "--run-id", view["run_id"], project="invalid")[1]["category"]
        == "authorization"
    )
    assert call("status")[1]["category"] == "input"
    assert call("start", "--item", "GPU-A", "--as-of", "malformed")[1]["category"] == "input"
    assert (
        call("start", "--item", "unobserved-item", "--as-of", "2026-10-01T00:00:00Z")[1]["category"]
        == "input"
    )
