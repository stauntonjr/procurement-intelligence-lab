import json
import os
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from procurement_intelligence_lab import bootstrap
from tests.contract.test_dependency_store import declaration
from tests.contract.test_document_review_journal import setup
from tests.integration.test_document_review_cli import run_cli as review_cli

pytestmark = pytest.mark.integration


def run_cli(dsn: str, *args: str, actor: bool = True):
    env = {**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": dsn}
    if actor:
        env["PIL_DOCUMENT_REVIEWER_ID"] = "impact-human"
    else:
        env.pop("PIL_DOCUMENT_REVIEWER_ID", None)
    return subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.correction_impact", *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_real_cli_register_restart_and_approved_impact(archive_dsn: str, tmp_path: Path):
    _, archive, p, content = setup(archive_dsn, tmp_path)
    (tmp_path / "source.xlsx").unlink()
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    proposal = tmp_path / "proposal.json"
    proposal.write_text(
        json.dumps(
            {
                "request_id": "impact-proposal",
                "snapshot_id": p.snapshot_id,
                "assertion_id": p.previous.assertion_id,
                "workflow": "document_value",
                "proposed_value": {"type": "decimal", "value": "0.00"},
                "reason": "Checked original",
            }
        )
    )
    first = review_cli(archive_dsn, "propose", "--scope", str(scope), "--input", str(proposal))
    assert first.returncode == 0, first.stderr
    task = json.loads(first.stdout)["task"]
    decision = tmp_path / "decision.json"
    decision.write_text(
        json.dumps(
            {
                "request_id": "impact-decision",
                "task_id": task["task_id"],
                "task_digest": task["digest"],
                "outcome": "approve",
                "reason": "Confirmed",
            }
        )
    )
    approved = review_cli(archive_dsn, "decide", "--scope", str(scope), "--input", str(decision))
    assert approved.returncode == 0, approved.stderr
    assert run_cli(archive_dsn, "init").returncode == 0
    manifest = tmp_path / "manifest.json"
    manifest.write_text(bootstrap.archive_codec().dumps(declaration(p)))
    args = ("register", "--scope", str(scope), "--input", str(manifest))
    registered = run_cli(archive_dsn, *args)
    assert registered.returncode == 0, registered.stderr
    assert run_cli(archive_dsn, *args).stdout == registered.stdout
    saved = json.loads(registered.stdout)
    assert saved["recorder_id"] == "impact-human"
    inspect = (
        "inspect",
        "--scope",
        str(scope),
        "--snapshot-id",
        saved["dependency_snapshot_id"],
        "--task-id",
        task["task_id"],
        "--as-of",
        datetime.now(UTC).isoformat(),
    )
    result = run_cli(archive_dsn, *inspect, "--max-depth", "1")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [x["reference_id"] for x in payload["affected"]] == ["state"]
    assert payload["frontier"] == ["fact"] and not payload["traversal_complete"]
    assert payload["review"] == json.loads(approved.stdout)
    assert payload["review"]["correction"]["value"] == {"type": "decimal", "value": "0.00"}
    assert payload["global_completeness"] == "not_evaluated"
    assert payload["dependency_snapshot"]["basis"] == "caller_declared_producer_receipts"
    complete = run_cli(archive_dsn, *inspect, "--max-depth", "32")
    assert [x["reference_id"] for x in json.loads(complete.stdout)["affected"]] == ["fact", "state"]
    before = run_cli(archive_dsn, *inspect, "--as-of", task["recorded_at"])
    assert before.returncode == 2 and not before.stdout
    assert archive.content(p.scope, p.snapshot_id) == content
    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps(asdict(replace(p.scope, version="other"))))
    denied = run_cli(archive_dsn, "register", "--scope", str(foreign), "--input", str(manifest))
    assert denied.returncode == 2 and not denied.stdout


@pytest.mark.parametrize(
    "raw",
    [
        "{}",
        "[]",
        "[ " * 12000 + "] " * 12000,
        '{"schema":1,"schema":1}',
        '"bad\\ud800text"',
        "x" * (1024 * 1024 + 1),
    ],
    ids=["object", "array", "deep", "duplicate", "surrogate", "oversized"],
)
def test_malformed_producer_manifest_fails_typed_without_writes(
    archive_dsn: str, tmp_path: Path, raw: str
):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    assert run_cli(archive_dsn, "init").returncode == 0
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    manifest = tmp_path / "bad.json"
    manifest.write_text(raw)
    result = run_cli(archive_dsn, "register", "--scope", str(scope), "--input", str(manifest))
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.dependency_contract_invalid"
    import psycopg

    with psycopg.connect(archive_dsn) as c:
        assert c.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_missing_identity_and_unavailable_backend_are_typed(archive_dsn: str, tmp_path: Path):
    _, _, p, _ = setup(archive_dsn, tmp_path)
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    raw = tmp_path / "manifest.json"
    raw.write_text(bootstrap.archive_codec().dumps(declaration(p)))
    denied = run_cli(
        archive_dsn, "register", "--scope", str(scope), "--input", str(raw), actor=False
    )
    assert denied.returncode == 2 and not denied.stdout
    assert json.loads(denied.stderr)["category"] == "authorization"
    unavailable = run_cli("postgresql://private:secret@127.0.0.1:1/private", "init")
    assert unavailable.returncode == 2 and not unavailable.stdout
    assert json.loads(unavailable.stderr)["code"] == "pil.infrastructure.dependency_unavailable"
    assert "secret" not in unavailable.stderr
