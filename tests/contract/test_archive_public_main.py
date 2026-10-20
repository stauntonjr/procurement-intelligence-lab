import json
import sys
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces import assertion_archive, bom_stages
from tests.bom_stage_fixtures import HEADER, ROW, workbook
from tests.integration.test_bom_normalization_cli import policy_file
from tests.integration.test_bom_stages_cli import CONTEXT

pytestmark = pytest.mark.contract


def test_public_parser_paths_retain_snapshot_after_source_is_gone(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setattr(sys, "argv", ["archive", "init"])
    assert assertion_archive.main() == 0
    assert json.loads(capsys.readouterr().out)["initialized"]
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    content = path.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bom",
            str(path),
            "--context",
            str(CONTEXT),
            "--normalization-policy",
            str(policy_file(tmp_path)),
            "--assertions",
            "--archive",
        ],
    )
    assert bom_stages.main() == 0
    payload = json.loads(capsys.readouterr().out)
    receipt = payload["archive_receipt"]
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(receipt["scope"]))
    path.unlink()
    for command in ("show", "history", "content"):
        args = ["archive", command, "--scope", str(scope)]
        if command != "history":
            args += ["--snapshot-id", receipt["snapshot_id"]]
        if command == "content":
            args += ["--output", str(tmp_path / "retained.xlsx")]
        monkeypatch.setattr(sys, "argv", args)
        assert assertion_archive.main() == 0
        result = json.loads(capsys.readouterr().out)
        if command == "show":
            assert result == payload
        elif command == "history":
            assert result["receipts"] == [receipt]
        else:
            assert (tmp_path / "retained.xlsx").read_bytes() == content
    monkeypatch.setattr(
        sys, "argv", ["archive", "show", "--scope", str(scope), "--snapshot-id", "absent"]
    )
    assert assertion_archive.main() == 2
    failure = capsys.readouterr()
    assert not failure.out
    assert json.loads(failure.err)["code"] == "pil.input.archive_not_found"
    monkeypatch.setattr(sys, "argv", ["bom", "absent", "--context", str(CONTEXT), "--archive"])
    assert bom_stages.main() == 2
    failure = capsys.readouterr()
    assert not failure.out
    assert json.loads(failure.err)["code"] == "pil.input.document_stage_invalid"
