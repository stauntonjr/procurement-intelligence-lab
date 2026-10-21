import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.contract.test_archived_bom_query import setup
from tests.integration.test_correction_impact_cli import run_cli as impact_cli
from tests.integration.test_document_review_cli import run_cli as review_cli

pytestmark = pytest.mark.integration


def run_cli(dsn: str, *args: str, actor: bool = True):
    env = {**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": dsn}
    if actor:
        env["PIL_DOCUMENT_REVIEWER_ID"] = "producer-human"
    else:
        env.pop("PIL_DOCUMENT_REVIEWER_ID", None)
    return subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.archived_bom_query", *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def files(tmp_path: Path, scope_data: object):
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(scope_data))
    context = tmp_path / "query-context.json"
    context.write_text(
        json.dumps(
            {
                "run_id": "cli-query-run",
                "code_revision": "test-revision",
                "started_at": datetime.now(UTC).isoformat(),
            }
        )
    )
    return scope, context


def test_actual_producer_cli_to_exact_approved_source_correction_impact(
    archive_dsn: str, tmp_path: Path
):
    _, archive, p, content = setup(archive_dsn, tmp_path)
    (tmp_path / "source.xlsx").unlink()
    assert impact_cli(archive_dsn, "init").returncode == 0
    scope, context = files(tmp_path, asdict(p.scope))
    args = (
        "--scope",
        str(scope),
        "--snapshot-id",
        p.snapshot_id,
        "--request-id",
        "query-cli",
        "--context",
        str(context),
    )
    result = run_cli(archive_dsn, *args)
    assert result.returncode == 0, result.stderr
    assert run_cli(archive_dsn, *args).stdout == result.stdout
    payload = json.loads(result.stdout)
    query = payload["query"]
    dependency = payload["dependency_snapshot"]
    assert query["value"] == ["GPU-A"] and query["status"] == "observed"
    assert (
        query["canonical_identity_established"] is False and query["corrections_applied"] is False
    )
    assert query["inputs"][0]["evidence"]["cells"] == ["A"]
    assert (
        payload["producer_execution"] == "synchronous_local_query"
        and not payload["query_result_materialized"]
    )
    assert dependency["recorder_id"] == "producer-human"
    proposal = tmp_path / "sku-proposal.json"
    proposal.write_text(
        json.dumps(
            {
                "request_id": "sku-correction",
                "snapshot_id": p.snapshot_id,
                "assertion_id": query["inputs"][0]["assertion_id"],
                "workflow": "document_value",
                "proposed_value": {"type": "str", "value": "GPU-B"},
                "reason": "Checked original source",
            }
        )
    )
    proposed = review_cli(archive_dsn, "propose", "--scope", str(scope), "--input", str(proposal))
    assert proposed.returncode == 0, proposed.stderr
    task = json.loads(proposed.stdout)["task"]
    decision = tmp_path / "sku-decision.json"
    decision.write_text(
        json.dumps(
            {
                "request_id": "sku-approve",
                "task_id": task["task_id"],
                "task_digest": task["digest"],
                "outcome": "approve",
                "reason": "Confirmed source",
            }
        )
    )
    accepted = review_cli(archive_dsn, "decide", "--scope", str(scope), "--input", str(decision))
    assert accepted.returncode == 0, accepted.stderr
    impact = impact_cli(
        archive_dsn,
        "inspect",
        "--scope",
        str(scope),
        "--snapshot-id",
        dependency["dependency_snapshot_id"],
        "--task-id",
        task["task_id"],
        "--as-of",
        datetime.now(UTC).isoformat(),
    )
    assert impact.returncode == 0, impact.stderr
    report = json.loads(impact.stdout)
    assert [x["reference_id"] for x in report["affected"]] == [query["reference_id"]]
    assert report["recomputation_executed"] is False
    assert run_cli(archive_dsn, *args).stdout == result.stdout
    assert archive.content(p.scope, p.snapshot_id) == content
    bad = run_cli(archive_dsn, *args, "--snapshot-id", "private\udcffid")
    assert bad.returncode == 2 and not bad.stdout
    assert json.loads(bad.stderr)["code"] == "pil.input.source_query_invalid"
    assert "private" not in bad.stderr


@pytest.mark.parametrize(
    "raw",
    [
        "{}",
        "[]",
        '{"run_id":"a","run_id":"b"}',
        "[" * 12000 + "]" * 12000,
        '{"run_id":"bad\\ud800","code_revision":"v","started_at":"2026-10-21T00:00:00+00:00"}',
        '{"run_id":"r","code_revision":"v","started_at":"2026-10-21"}',
        '{"run_id":"r","code_revision":"v","started_at":"2099-01-01T00:00:00+00:00"}',
        "x" * 32769,
    ],
    ids=["missing", "array", "duplicate", "depth", "unicode", "naive", "future", "oversized"],
)
def test_bad_run_context_is_typed_and_cannot_register(archive_dsn: str, tmp_path: Path, raw: str):
    import psycopg

    _, _, p, _ = setup(archive_dsn, tmp_path)
    assert impact_cli(archive_dsn, "init").returncode == 0
    scope, context = files(tmp_path, asdict(p.scope))
    context.write_text(raw)
    result = run_cli(
        archive_dsn,
        "--scope",
        str(scope),
        "--snapshot-id",
        p.snapshot_id,
        "--request-id",
        "invalid",
        "--context",
        str(context),
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.source_query_invalid"
    with psycopg.connect(archive_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM pil_dependency_snapshots").fetchone() == (0,)


def test_cli_missing_identity_and_parse_errors_are_sanitized(tmp_path: Path):
    scope, context = files(
        tmp_path, {"tenant_id": "synthetic", "project_id": "p", "site_id": "lab", "version": "1"}
    )
    args = (
        "--scope",
        str(scope),
        "--snapshot-id",
        "snapshot",
        "--request-id",
        "request",
        "--context",
        str(context),
    )
    denied = run_cli("configured-unused", *args, actor=False)
    assert denied.returncode == 2 and json.loads(denied.stderr)["category"] == "authorization"
    for flags in [(), (*args, "--unknown", "private-invalid")]:
        result = run_cli("configured-unused", *flags)
        assert result.returncode == 2 and not result.stdout
        assert json.loads(result.stderr)["code"] == "pil.input.source_query_invalid"
        assert "private-invalid" not in result.stderr
