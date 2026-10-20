import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.contract.test_document_review_journal import setup

pytestmark = pytest.mark.integration


def run_cli(archive_dsn: str, *args: str, actor: bool = True):
    env = {**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": archive_dsn}
    if actor:
        env["PIL_DOCUMENT_REVIEWER_ID"] = "human-cli"
    else:
        env.pop("PIL_DOCUMENT_REVIEWER_ID", None)
    return subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.document_review", *args],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_real_cli_exact_review_survives_restart_and_historical_read(
    archive_dsn: str, tmp_path: Path
):
    _, archive, p, content = setup(archive_dsn, tmp_path)
    (tmp_path / "source.xlsx").unlink()
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    proposal = tmp_path / "proposal.json"
    proposal.write_text(
        json.dumps(
            {
                "request_id": "cli-1",
                "snapshot_id": p.snapshot_id,
                "assertion_id": p.previous.assertion_id,
                "workflow": "document_value",
                "proposed_value": {"type": "decimal", "value": "8.00"},
                "reason": "Correct interpreted value",
            }
        )
    )
    args = ("propose", "--scope", str(scope), "--input", str(proposal))
    first = run_cli(archive_dsn, *args)
    assert first.returncode == 0, first.stderr
    assert run_cli(archive_dsn, *args).stdout == first.stdout
    task = json.loads(first.stdout)["task"]
    decision = tmp_path / "decision.json"
    command = {
        "request_id": "decision-cli-1",
        "task_id": task["task_id"],
        "task_digest": task["digest"],
        "outcome": "approve",
        "reason": "Checked the captured original",
    }
    decision.write_text(json.dumps({**command, "task_digest": "0" * 64}))
    bad = run_cli(archive_dsn, "decide", "--scope", str(scope), "--input", str(decision))
    assert bad.returncode == 2 and not bad.stdout
    assert json.loads(bad.stderr)["code"] == "pil.policy.document_review_conflict"
    decision.write_text(json.dumps(command))
    approved = run_cli(archive_dsn, "decide", "--scope", str(scope), "--input", str(decision))
    assert approved.returncode == 0, approved.stderr
    result = json.loads(approved.stdout)
    assert result["correction"]["value"] == {"type": "decimal", "value": "8.00"}
    assert result["correction"]["recomputation_required"] is True
    assert result["correction"]["downstream_status"] == "not_evaluated"
    assert result["correction"]["governing_state_updated"] is False
    assert result["task"]["previous_value"] == {"type": "decimal", "value": "0.5"}
    assert result["task"]["evidence"]["cells"] == ["C"]
    assert (
        run_cli(archive_dsn, "decide", "--scope", str(scope), "--input", str(decision)).stdout
        == approved.stdout
    )
    shown = run_cli(archive_dsn, "show", "--scope", str(scope), "--task-id", task["task_id"])
    assert json.loads(shown.stdout) == result
    before = run_cli(
        archive_dsn,
        "show",
        "--scope",
        str(scope),
        "--task-id",
        task["task_id"],
        "--as-of",
        task["recorded_at"],
    )
    assert json.loads(before.stdout)["decision"] is None
    assert json.loads(before.stdout)["correction"] is None
    assert archive.content(p.scope, p.snapshot_id) == content
    history = run_cli(archive_dsn, "history", "--scope", str(scope))
    assert len(json.loads(history.stdout)["reviews"]) == 1
    scope.write_text(json.dumps({**asdict(p.scope), "version": "foreign"}))
    denied = run_cli(archive_dsn, "show", "--scope", str(scope), "--task-id", task["task_id"])
    assert denied.returncode == 2 and not denied.stdout
    assert json.loads(denied.stderr)["code"] == "pil.input.document_review_not_found"


def test_cli_rejects_untrusted_authority_and_unsupported_input(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    request = tmp_path / "request.json"
    base = {
        "request_id": "cli",
        "snapshot_id": p.snapshot_id,
        "assertion_id": p.previous.assertion_id,
        "workflow": "document_value",
        "proposed_value": {"type": "decimal", "value": "8"},
        "reason": "correct",
    }
    for changes in (
        {"reviewer_id": "spoof"},
        {"permissions": ["review"]},
        {"recorded_at": "2020-01-01"},
        {"workflow": "entity"},
        {"proposed_value": {"type": "decimal", "value": 8.5}},
    ):
        request.write_text(json.dumps({**base, **changes}))
        bad = run_cli(archive_dsn, "propose", "--scope", str(scope), "--input", str(request))
        assert bad.returncode == 2 and not bad.stdout
        assert json.loads(bad.stderr)["code"].startswith("pil.input.")
    missing = run_cli(archive_dsn, "history", "--scope", str(scope), actor=False)
    assert missing.returncode == 2 and not missing.stdout
    assert json.loads(missing.stderr)["code"] == "pil.input.document_review_contract_invalid"


@pytest.mark.parametrize("malformed", ["surrogate", "deep_json", "deep_scope"])
def test_malformed_unicode_and_depth_fail_typed_without_committing(
    archive_dsn: str, tmp_path: Path, malformed: str
):
    journal, _, p, _ = setup(archive_dsn, tmp_path)
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    request = tmp_path / "malformed.json"
    payload = {
        "request_id": "malformed",
        "snapshot_id": p.snapshot_id,
        "assertion_id": p.previous.assertion_id,
        "workflow": "document_value",
        "proposed_value": {"type": "decimal", "value": "8"},
        "reason": "bad" + chr(0xD800) + "text",
    }
    request.write_text(
        json.dumps(payload) if malformed == "surrogate" else "[" * 15000 + "0" + "]" * 15000
    )
    if malformed == "deep_scope":
        scope.write_text("[" * 15000 + "0" + "]" * 15000)
    result = run_cli(archive_dsn, "propose", "--scope", str(scope), "--input", str(request))
    assert result.returncode == 2 and not result.stdout
    expected_code = (
        "pil.input.archive_contract_invalid"
        if malformed == "deep_scope"
        else "pil.input.document_review_contract_invalid"
    )
    assert json.loads(result.stderr)["code"] == expected_code
    assert journal.history(p.scope) == ()
