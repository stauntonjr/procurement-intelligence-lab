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
