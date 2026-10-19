"""Public manifest command: canonical bytes, no source I/O and closed profile selection."""

import json
import subprocess
import sys
from hashlib import sha256

import pytest


@pytest.mark.integration
def test_manifest_cli_compiles_the_real_package_identically_across_processes() -> None:
    command = [sys.executable, "-m", "procurement_intelligence_lab.interfaces.domain_package"]
    runs = [subprocess.run(command, capture_output=True, check=False) for _ in range(2)]
    assert all(run.returncode == 0 for run in runs), [run.stderr for run in runs]
    assert runs[0].stdout == runs[1].stdout
    manifest = json.loads(runs[0].stdout)
    assert manifest["domain"]["id"] == "procurement"
    assert manifest["source_profile"]["id"] == "bom-table"
    assert len(manifest["stages"]) == 12
    from procurement_intelligence_lab.bootstrap import compile_procurement_manifest

    expected = compile_procurement_manifest()
    assert runs[0].stdout == expected.canonical_json + b"\n"
    assert sha256(runs[0].stdout.rstrip(b"\n")).hexdigest() == expected.manifest_hash


@pytest.mark.integration
@pytest.mark.parametrize("profile", ["", "purchase-order", "bom-table ", "BOM-TABLE"])
def test_manifest_cli_rejects_unknown_profile_without_defaulting(profile: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.domain_package",
            "--source-profile",
            profile,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["code"] == "pil.input.domain_package_invalid"
    assert error["category"] == "input"
    assert any(issue["code"] == "unknown_source_profile" for issue in error["issues"])
