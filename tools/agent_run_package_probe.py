"""Exercise two real installed CLI processes against one durable local ledger."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    command = [
        sys.executable,
        "-m",
        "procurement_intelligence_lab.interfaces.agent_runs",
        "--database",
        str(Path(directory) / "runs.db"),
    ]
    created = subprocess.run(
        command + ["create", "--project", "atlas"], check=True, capture_output=True, text=True
    )
    run = json.loads(created.stdout)
    resumed = subprocess.run(
        command + ["resume", "--project", "atlas", "--run-id", run["run_id"]],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(resumed.stdout) == run
    denied = subprocess.run(
        command + ["resume", "--project", "delta", "--run-id", run["run_id"]],
        check=False,
        capture_output=True,
        text=True,
    )
    assert (
        denied.returncode != 0
        and json.loads(denied.stdout)["code"] == "pil.input.agent_run_not_found"
    )
    print("installed run CLI: durable resume and foreign scope denial passed")


with tempfile.TemporaryDirectory() as directory:
    command = [
        sys.executable,
        "-m",
        "procurement_intelligence_lab.interfaces.agent_runs",
        "--database",
        str(Path(directory) / "tools.db"),
    ]
    run = json.loads(
        subprocess.run(
            command + ["create", "--project", "atlas"], check=True, capture_output=True, text=True
        ).stdout
    )
    args = ["--project", "atlas", "--run-id", run["run_id"]]
    result = json.loads(
        subprocess.run(
            command
            + ["investigate", *args, "--item", "GPU-A", "--as-of", "2026-10-01T00:00:00+00:00"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )["result"]
    assert result["required_quantity"] == "8" and result["ordered_quantity"] == "6"
    source = json.loads(
        subprocess.run(
            command + ["source", *args, "--evidence-id", result["evidence"][0]["evidence_id"]],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )["result"]
    assert source["cells"][0] == "GPU-A"
    finished = json.loads(
        subprocess.run(
            command + ["finish", *args], check=True, capture_output=True, text=True
        ).stdout
    )
    assert finished["trajectory"]["outcome"] == "pass" and finished["trajectory"]["tool_calls"] == 2
    assert finished["summary"]["live_counts"]["pass"] == 0
    print(
        "installed corpus tools: authoritative quantities, original source and audited fixture trajectory passed"
    )

with tempfile.TemporaryDirectory() as directory:
    database = str(Path(directory) / "briefs.db")
    root = [
        sys.executable,
        "-m",
        "procurement_intelligence_lab.interfaces.agent_runs",
        "--database",
        database,
    ]
    run = json.loads(
        subprocess.run(
            root + ["create", "--project", "atlas"], check=True, capture_output=True, text=True
        ).stdout
    )
    human = [
        sys.executable,
        "-m",
        "procurement_intelligence_lab.interfaces.briefs",
        "--database",
        database,
    ]
    scope = ["--project", "atlas", "--run-id", run["run_id"]]
    brief = json.loads(
        subprocess.run(
            human + ["draft", *scope, "--item", "GPU-A", "--as-of", "2026-10-01T00:00:00Z"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert json.loads(brief["content_json"])["required_quantity"] == "8"
    exact = [*scope, "--brief-id", brief["brief_id"], "--digest", brief["digest"]]
    denied = subprocess.run(
        human + ["save", *exact, "--idempotency-key", brief["idempotency_key"]],
        check=False,
        capture_output=True,
        text=True,
    )
    assert denied.returncode == 1 and json.loads(denied.stdout)["category"] == "policy"
    receipt = json.loads(
        subprocess.run(
            human + ["review", *exact, "--decision", "approve"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert receipt["digest"] == brief["digest"] and receipt["decision"] == "approve"
    save = human + ["save", *exact, "--idempotency-key", brief["idempotency_key"]]
    first = json.loads(subprocess.run(save, check=True, capture_output=True, text=True).stdout)
    replay = json.loads(subprocess.run(save, check=True, capture_output=True, text=True).stdout)
    assert first == replay and first["brief_id"] == brief["brief_id"]
    print("installed human brief CLI: exact approval and durable single-save replay passed")
