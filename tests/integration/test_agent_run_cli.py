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


def test_actual_tools_then_finish_in_separate_processes(tmp_path: Path) -> None:
    db = tmp_path / "runs.db"
    run = json.loads(invoke(db, "create", "--project", "atlas").stdout)
    arguments = ("--project", "atlas", "--run-id", run["run_id"])
    investigated = invoke(
        db, "investigate", *arguments, "--item", "GPU-A", "--as-of", "2026-10-01T00:00:00+00:00"
    )
    assert investigated.returncode == 0, investigated.stderr
    result = json.loads(investigated.stdout)["result"]
    assert result["required_quantity"] == "8" and result["ordered_quantity"] == "6"
    assert result["status"] == "anomaly" and result["snapshot_id"]
    inspected = invoke(
        db, "source", *arguments, "--evidence-id", result["evidence"][0]["evidence_id"]
    )
    assert inspected.returncode == 0, inspected.stderr
    source = json.loads(inspected.stdout)["result"]
    assert source["cells"][0] == "GPU-A" and source["evidence"] == {
        k: v for k, v in result["evidence"][0].items() if k != "url"
    }
    finished = invoke(db, "finish", *arguments)
    assert finished.returncode == 0, finished.stderr
    report = json.loads(finished.stdout)
    assert report["trajectory"]["outcome"] == "pass" and report["trajectory"]["tool_calls"] == 2
    assert report["summary"]["live_counts"]["pass"] == 0
    repeated = invoke(db, "finish", *arguments)
    assert repeated.returncode == 0 and json.loads(repeated.stdout) == report


def test_missing_and_failed_tools_cannot_finish_successfully(tmp_path: Path) -> None:
    db = tmp_path / "runs.db"
    run = json.loads(invoke(db, "create", "--project", "atlas").stdout)
    args = ("--project", "atlas", "--run-id", run["run_id"])
    source = invoke(db, "source", *args, "--evidence-id", "unknown")
    assert (
        source.returncode != 0
        and json.loads(source.stdout)["code"] == "pil.input.agent_tool_invalid_result"
    )
    finished = invoke(db, "finish", *args)
    assert (
        finished.returncode != 0 and json.loads(finished.stdout)["trajectory"]["outcome"] == "fail"
    )
    empty = json.loads(invoke(db, "create", "--project", "atlas").stdout)
    missing = invoke(db, "finish", "--project", "atlas", "--run-id", empty["run_id"])
    assert (
        missing.returncode != 0 and json.loads(missing.stdout)["trajectory"]["outcome"] == "unknown"
    )


def test_cli_run_build_identity_is_code_digest(tmp_path: Path) -> None:
    created = invoke(tmp_path / "r.db", "create", "--project", "atlas")
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["versions"]["application"].startswith("sha256:"), (
        "CLI build identity is only a package version"
    )
