import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, workbook
from tests.integration.test_bom_normalization_cli import policy_file
from tests.integration.test_bom_stages_cli import CONTEXT

pytestmark = pytest.mark.integration


def invoke(dsn: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *argv],
        env={**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": dsn},
        capture_output=True,
        text=True,
        check=False,
    )


def test_real_cli_survives_source_deletion_and_restart(archive_dsn: str, tmp_path: Path) -> None:
    init = invoke(
        archive_dsn, ["procurement_intelligence_lab.interfaces.assertion_archive", "init"]
    )
    assert init.returncode == 0, init.stderr
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    content = path.read_bytes()
    command = [
        "procurement_intelligence_lab.interfaces.bom_stages",
        str(path),
        "--context",
        str(CONTEXT),
        "--normalization-policy",
        str(policy_file(tmp_path)),
        "--assertions",
        "--archive",
    ]
    first = invoke(archive_dsn, command)
    assert first.returncode == 0, first.stderr
    again = invoke(archive_dsn, command)
    assert again.stdout == first.stdout
    payload = json.loads(first.stdout)
    receipt = payload["archive_receipt"]
    assert len(payload["transformations"]) == 5
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(receipt["scope"]))
    base = ["procurement_intelligence_lab.interfaces.assertion_archive"]
    path.unlink()
    shown = invoke(
        archive_dsn, [*base, "show", "--scope", str(scope), "--snapshot-id", receipt["snapshot_id"]]
    )
    assert shown.returncode == 0, shown.stderr
    assert json.loads(shown.stdout) == payload
    output = tmp_path / "retained.xlsx"
    exported = invoke(
        archive_dsn,
        [
            *base,
            "content",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
            "--output",
            str(output),
        ],
    )
    assert exported.returncode == 0, exported.stderr
    assert output.read_bytes() == content
    existing = invoke(
        archive_dsn,
        [
            *base,
            "content",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
            "--output",
            str(output),
        ],
    )
    assert existing.returncode == 2 and not existing.stdout and output.read_bytes() == content
    history = invoke(archive_dsn, [*base, "history", "--scope", str(scope)])
    assert json.loads(history.stdout)["receipts"] == [receipt]
    scope.write_text(json.dumps({**receipt["scope"], "tenant_id": "foreign"}))
    absent = invoke(
        archive_dsn, [*base, "show", "--scope", str(scope), "--snapshot-id", receipt["snapshot_id"]]
    )
    assert absent.returncode == 2 and not absent.stdout
    assert json.loads(absent.stderr)["code"] == "pil.input.archive_not_found"


def test_archive_requires_assertions_and_missing_configuration_fails_typed(tmp_path: Path) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    args = [
        "procurement_intelligence_lab.interfaces.bom_stages",
        str(path),
        "--context",
        str(CONTEXT),
        "--archive",
    ]
    result = invoke("", args)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.document_stage_invalid"
    result = invoke("", ["procurement_intelligence_lab.interfaces.assertion_archive", "init"])
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.archive_contract_invalid"


def test_database_failure_and_invalid_scope_are_sanitized(tmp_path: Path) -> None:
    dsn = "postgresql://invalid:canary-not-a-real-secret@127.0.0.1:1/unused"
    result = invoke(dsn, ["procurement_intelligence_lab.interfaces.assertion_archive", "init"])
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.infrastructure.archive_unavailable"
    assert "canary-not-a-real-secret" not in result.stderr and "127.0.0.1" not in result.stderr
    scope = tmp_path / "scope.json"
    scope.write_text("[]")
    result = invoke(
        dsn,
        [
            "procurement_intelligence_lab.interfaces.assertion_archive",
            "history",
            "--scope",
            str(scope),
        ],
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.archive_contract_invalid"
