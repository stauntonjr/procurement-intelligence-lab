"""Fresh processes recover archived reconciliation and original companion source exports."""

import json
from pathlib import Path

import psycopg
import pytest

from tests.integration.test_planned_execution_archive_cli import failure, run, success
from tests.reconciliation_public_fixtures import inputs

pytestmark = pytest.mark.integration


def test_restart_delete_input_files_show_history_manifest_export(archive_dsn: str, tmp_path: Path):
    args, scope, ps = inputs(tmp_path, archive_dsn)
    failure(
        run("reconcile_resolved_package", args + ["--archive"], archive_dsn),
        "pil.infrastructure.archive_unavailable",
    )
    success(run("reconciliation_archive", ["init"], archive_dsn))
    first = success(run("reconcile_resolved_package", args + ["--archive"], archive_dsn))
    key = first["current_operation"]["execution_digest"]
    source = (tmp_path / "producer-0/source.xlsx").read_bytes()
    for flag in (
        "--manifest",
        "--registry",
        "--config",
        "--context",
        "--governing-policy",
        "--authority",
    ):
        Path(args[args.index(flag) + 1]).unlink()
    for p in (tmp_path / "producer-0").iterdir():
        p.unlink()
    base = ["--scope", str(scope), "--execution-digest", key]
    shown = success(run("reconciliation_archive", ["show", *base], archive_dsn))
    assert shown["current_operation"] == first["first_retained_operation"]
    page = success(
        run(
            "reconciliation_archive",
            ["history", "--scope", str(scope), "--limit", "1"],
            archive_dsn,
        )
    )
    assert page["receipts"] == [first["archive_receipt"]] and not page["has_more"]
    manifest = success(run("reconciliation_archive", ["content-manifest", *base], archive_dsn))
    assert manifest["original_source_bytes_included"] is False
    output = tmp_path / "retained.json"
    cmd = ["export", *base, "--output", str(output)]
    success(run("reconciliation_archive", cmd, archive_dsn))
    failure(run("reconciliation_archive", cmd, archive_dsn), "pil.input.archive_contract_invalid")
    assert output.is_file()
    src = tmp_path / "recovered.xlsx"
    success(
        run(
            "resolved_execution_archive",
            [
                "content",
                "--scope",
                str(scope),
                "--execution-digest",
                ps[0]["execution_receipt"]["execution_digest"],
                "--output",
                str(src),
            ],
            archive_dsn,
        )
    )
    assert src.read_bytes() == source
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_reconciliation_producers DISABLE TRIGGER USER")
        conn.execute("DELETE FROM pil_reconciliation_producers")
    failure(
        run("reconciliation_archive", ["show", *base], archive_dsn),
        "pil.infrastructure.archive_integrity_invalid",
    )


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["show"],
        ["history", "--scope", "missing", "--limit", "201"],
        ["history", "--scope", "missing", "--after-sequence", "-1"],
        ["export", "--scope", "missing", "--execution-digest", "bad", "--output", "missing"],
    ],
)
def test_archive_argument_errors_are_json(args: list[str]):
    result = run("reconciliation_archive", args, "postgresql://invalid:1/must-not-connect")
    assert result.returncode == 2 and not result.stdout and "Traceback" not in result.stderr
    assert json.loads(result.stderr)["code"] == "pil.input.archive_contract_invalid"


def test_public_history_gaps_pagination_and_foreign_scope(archive_dsn: str, tmp_path: Path):
    args, scope, _ = inputs(tmp_path, archive_dsn)
    success(run("reconciliation_archive", ["init"], archive_dsn))
    first = success(run("reconcile_resolved_package", args + ["--archive"], archive_dsn))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("SELECT setval(pg_get_serial_sequence('pil_reconciliations','sequence'), 7)")
    args[args.index("--as-of") + 1] = "2026-10-18T00:00:00Z"
    second = success(run("reconcile_resolved_package", args + ["--archive"], archive_dsn))
    assert second["archive_receipt"]["sequence"] == 8
    page = success(
        run(
            "reconciliation_archive",
            ["history", "--scope", str(scope), "--limit", "1"],
            archive_dsn,
        )
    )
    assert page["has_more"] and page["receipts"] == [first["archive_receipt"]]
    after = success(
        run(
            "reconciliation_archive",
            [
                "history",
                "--scope",
                str(scope),
                "--limit",
                "200",
                "--after-sequence",
                str(page["next_after_sequence"]),
            ],
            archive_dsn,
        )
    )
    assert after["receipts"] == [second["archive_receipt"]] and not after["has_more"]
    wrong = tmp_path / "foreign-scope.json"
    foreign = json.loads(scope.read_text())
    foreign["version"] = "foreign-version"
    wrong.write_text(json.dumps(foreign))
    failure(
        run(
            "reconciliation_archive",
            [
                "show",
                "--scope",
                str(wrong),
                "--execution-digest",
                first["current_operation"]["execution_digest"],
            ],
            archive_dsn,
        ),
        "pil.input.archive_not_found",
    )
