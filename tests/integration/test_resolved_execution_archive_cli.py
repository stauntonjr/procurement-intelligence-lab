"""Real database and fresh processes recover exact source and catalog evidence."""

import json
from pathlib import Path

import psycopg
import pytest

from tests.integration.test_execute_resolved_package_cli import inputs
from tests.integration.test_planned_execution_archive_cli import failure, run, success

pytestmark = pytest.mark.integration


def test_restart_delete_source_files_recover_and_export(archive_dsn: str, tmp_path: Path):
    args = inputs(tmp_path)
    source = Path(args[0]).read_bytes()
    catalog = Path(args[args.index("--candidate-snapshot") + 1]).read_bytes()
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps(json.loads(Path(args[args.index("--context") + 1]).read_text())["scope"])
    )
    failure(
        run("resolved_execution_archive", ["init"], archive_dsn),
        "pil.infrastructure.archive_unavailable",
    )
    for module in ("assertion_archive", "planned_execution_archive", "resolved_execution_archive"):
        success(run(module, ["init"], archive_dsn))
    # Retain first-five separately; real five-stage caller accepts the same six-stage plan.
    oldargs = args[: args.index("--resolution-policy")]
    oldargs[oldargs.index("--stop-after") + 1] = "ASSERT"
    five = success(run("execute_package", oldargs + ["--archive"], archive_dsn))
    first = success(run("execute_resolved_package", args + ["--archive"], archive_dsn))
    key = first["archive_receipt"]["execution_digest"]
    cp = Path(args[args.index("--candidate-snapshot") + 1])
    cp.write_text(json.dumps(json.loads(catalog), indent=2))
    again = success(run("execute_resolved_package", args + ["--archive"], archive_dsn))
    assert first["archive_receipt"] == again["archive_receipt"]
    assert (
        again["resolution"]["candidate_raw_sha256"] != first["resolution"]["candidate_raw_sha256"]
    )
    assert first["retained_prefix_execution_receipt"] == five["execution_receipt"]
    for flag in (
        "--manifest",
        "--registry",
        "--config",
        "--context",
        "--candidate-snapshot",
        "--resolution-policy",
    ):
        Path(args[args.index(flag) + 1]).unlink()
    Path(args[0]).unlink()
    base = ["--scope", str(scope), "--execution-digest", key]
    shown = success(run("resolved_execution_archive", ["show", *base], archive_dsn))
    assert shown["resolution"] == first["resolution"]
    page = success(
        run(
            "resolved_execution_archive",
            ["history", "--scope", str(scope), "--limit", "1"],
            archive_dsn,
        )
    )
    assert page["receipts"] == [first["archive_receipt"]]
    for command, data in (("content", source), ("export", None)):
        out = tmp_path / (command + ".bin")
        cmd = [command, *base, "--output", str(out)]
        success(run("resolved_execution_archive", cmd, archive_dsn))
        if data is not None:
            assert out.read_bytes() == data
        else:
            from procurement_intelligence_lab import bootstrap
            from procurement_intelligence_lab.platform.execution.resolution_archive import (
                ArchivedResolvedPrefix,
            )

            retained = bootstrap.archive_codec().loads(out.read_text())
            assert isinstance(retained, ArchivedResolvedPrefix)
            assert retained.completed.execution.candidate_input.raw_json == catalog
        failure(
            run("resolved_execution_archive", cmd, archive_dsn),
            "pil.input.archive_contract_invalid",
        )
    # Present but corrupt evidence must remain an integrity failure through the real public path.
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_resolved_executions DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_resolved_executions SET payload_sha256=%s", ("a" * 64,))
    failure(
        run("resolved_execution_archive", ["show", *base], archive_dsn),
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
def test_strict_archive_arguments_precede_storage(args: list[str]):
    failure(run("resolved_execution_archive", args, ""), "pil.input.archive_contract_invalid")
