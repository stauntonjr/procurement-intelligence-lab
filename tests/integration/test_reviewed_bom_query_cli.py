import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab import bootstrap
from tests.bom_stage_fixtures import AT
from tests.contract.test_reviewed_bom_query import approved
from tests.integration.test_archived_bom_query_cli import files
from tests.integration.test_correction_impact_cli import run_cli as impact_cli

pytestmark = pytest.mark.integration


def run_cli(dsn: str, *args: str, actor: bool = True):
    env = {**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": dsn}
    if actor:
        env["PIL_DOCUMENT_REVIEWER_ID"] = "reviewed-cli-human"
    else:
        env.pop("PIL_DOCUMENT_REVIEWER_ID", None)
    return subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.reviewed_bom_query", *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_actual_reviewed_cli_requires_explicit_capability_and_retries(
    archive_dsn: str, tmp_path: Path
):
    p, task, archive, content = approved(archive_dsn, tmp_path, capability=False)
    (tmp_path / "source.xlsx").unlink()
    scope, context = files(tmp_path, asdict(p.scope))
    reviews = tmp_path / "reviews.json"
    reviews.write_text(json.dumps({"task_ids": [task.task_id]}))
    args = (
        "--scope",
        str(scope),
        "--snapshot-id",
        p.snapshot_id,
        "--request-id",
        "reviewed-cli",
        "--reviews",
        str(reviews),
        "--as-of",
        (AT + timedelta(seconds=4)).isoformat(),
        "--context",
        str(context),
    )
    missing = run_cli(archive_dsn, *args)
    assert (
        missing.returncode == 2
        and not missing.stdout
        and json.loads(missing.stderr)["code"] == "pil.infrastructure.dependency_unavailable"
    )
    initialized = impact_cli(archive_dsn, "init-reviewed")
    assert initialized.returncode == 0, initialized.stderr
    assert json.loads(initialized.stdout)["capability"] == "approved_correction_roots/v1"
    result = run_cli(archive_dsn, *args)
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["reviewed_query"]["value"] == ["GPU-B"]
    assert body["reviewed_query"]["status"] == "inferred"
    assert body["recomputation_executed"] and not body["original_source_updated"]
    assert body["selected_reviews"][0]["task"]["task_id"] == task.task_id
    assert body["dependency_snapshot"]["recorder_id"] == "reviewed-cli-human"
    assert run_cli(archive_dsn, *args).stdout == result.stdout
    assert archive.content(p.scope, p.snapshot_id) == content
    graph = bootstrap.build_dependency_store(archive_dsn).get(
        p.scope, body["dependency_snapshot"]["dependency_snapshot_id"]
    )
    assert len(graph.manifest.roots) == 2 and len(graph.manifest.claims) == 2


@pytest.mark.parametrize(
    "raw",
    [
        b'{"task_ids":[],"task_ids":[]}',
        b'{"task_ids":[]}',
        b'{"task_ids":["x","x"]}',
        b'{"task_ids":["x"],"reviewer":"spoof"}',
        b"\xff",
        b" " * 32769,
    ],
    ids=[
        "duplicate_keys",
        "empty",
        "duplicate_ids",
        "authority_override",
        "invalid_utf8",
        "oversized",
    ],
)
def test_malformed_review_file_is_typed(archive_dsn: str, tmp_path: Path, raw: bytes):
    scope, context = files(
        tmp_path, {"tenant_id": "t", "project_id": "p", "site_id": "s", "version": "1"}
    )
    reviews = tmp_path / "reviews.json"
    reviews.write_bytes(raw)
    result = run_cli(
        archive_dsn,
        "--scope",
        str(scope),
        "--snapshot-id",
        "source",
        "--request-id",
        "r",
        "--reviews",
        str(reviews),
        "--as-of",
        AT.isoformat(),
        "--context",
        str(context),
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.source_query_invalid"
    assert "Traceback" not in result.stderr


def test_missing_identity_and_parser_errors_are_typed(archive_dsn: str, tmp_path: Path):
    result = run_cli(archive_dsn)
    assert (
        result.returncode == 2
        and json.loads(result.stderr)["code"] == "pil.input.source_query_invalid"
    )
    scope, context = files(
        tmp_path, {"tenant_id": "t", "project_id": "p", "site_id": "s", "version": "1"}
    )
    reviews = tmp_path / "reviews.json"
    reviews.write_text('{"task_ids":["x"]}')
    denied = run_cli(
        archive_dsn,
        "--scope",
        str(scope),
        "--snapshot-id",
        "source",
        "--request-id",
        "r",
        "--reviews",
        str(reviews),
        "--as-of",
        AT.isoformat(),
        "--context",
        str(context),
        actor=False,
    )
    assert denied.returncode == 2 and not denied.stdout
    assert json.loads(denied.stderr)["code"] == "pil.authorization.request_scope_denied"


def test_actual_cli_corrects_only_one_duplicate_source_row(archive_dsn: str, tmp_path: Path):
    from tests.bom_stage_fixtures import HEADER, ROW

    p, task, archive, _ = approved(archive_dsn, tmp_path, rows=HEADER + ROW + ROW.replace("7", "8"))
    scope, context = files(tmp_path, asdict(p.scope))
    selection = tmp_path / "duplicate-selection.json"
    selection.write_text(json.dumps({"task_ids": [task.task_id]}))
    result = run_cli(
        archive_dsn,
        "--scope",
        str(scope),
        "--snapshot-id",
        p.snapshot_id,
        "--request-id",
        "duplicate-row-replay",
        "--reviews",
        str(selection),
        "--as-of",
        (AT + timedelta(seconds=4)).isoformat(),
        "--context",
        str(context),
    )
    assert result.returncode == 0, result.stderr
    query = json.loads(result.stdout)["reviewed_query"]
    assert query["value"] == ["GPU-A", "GPU-B"] and len(query["reviewed_rows"]) == 1
    snapshot = archive.load(p.scope, p.snapshot_id)[1]
    assert [a.value for a in snapshot.assertions if a.predicate.value == "has_sku"] == [
        "GPU-A",
        "GPU-A",
    ]
