import json
import subprocess
import sys
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch

from procurement_intelligence_lab import __main__ as cli


def test_cli_runs_committed_synthetic_bom_demo() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab"],
        check=True,
        capture_output=True,
        cwd=repository_root,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["claims"]["bom_cost"]["value"] == "500"
    assert payload["claims"]["gpu_quantity"]["value"] == "4"
    assert payload["operational_state"][0]["canonical_key"] == "CPU-A"
    assert payload["evidence_chain"]["nodes"][-1]["status"] == "reconciled"


def test_cli_main_reads_packaged_default_resource(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["procurement-intelligence-lab"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["claims"]["bom_cost"]["value"] == "500"
