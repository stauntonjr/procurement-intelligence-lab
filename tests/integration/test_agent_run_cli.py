"""Actual subprocess restart with fixed server-owned synthetic authority."""

import json
import subprocess
import sys
from pathlib import Path


def invoke(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.agent_runs",
            "--database",
            str(path),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_create_and_resume_after_process_exit(tmp_path: Path) -> None:
    created = invoke(tmp_path / "runs.db", "create", "--project", "atlas")
    assert created.returncode == 0, created.stderr
    run = json.loads(created.stdout)
    assert run["execution_kind"] == "fixture" and run["tenant_id"] == "synthetic-tenant"
    resumed = invoke(
        tmp_path / "runs.db", "resume", "--project", "atlas", "--run-id", run["run_id"]
    )
    assert resumed.returncode == 0 and json.loads(resumed.stdout) == run
    foreign = invoke(
        tmp_path / "runs.db", "resume", "--project", "delta", "--run-id", run["run_id"]
    )
    assert (
        foreign.returncode != 0
        and json.loads(foreign.stdout)["code"] == "pil.input.agent_run_not_found"
    )
    unknown = invoke(tmp_path / "runs.db", "create", "--project", "foreign")
    assert (
        unknown.returncode != 0
        and json.loads(unknown.stdout)["code"] == "pil.authorization.request_scope_denied"
    )
    missing = invoke(tmp_path / "runs.db", "resume", "--project", "atlas")
    assert missing.returncode != 0


def test_storage_failure_remains_infrastructure(tmp_path: Path) -> None:
    failed = invoke(tmp_path / "missing" / "runs.db", "create", "--project", "atlas")
    assert (
        failed.returncode != 0
        and json.loads(failed.stdout)["code"] == "pil.infrastructure.agent_run_store_unavailable"
    )
