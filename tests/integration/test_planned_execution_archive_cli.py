import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import psycopg
import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError
from tests.integration.test_execute_package_cli import inputs

pytestmark = pytest.mark.integration
PREFIX = "procurement_intelligence_lab.interfaces."


def run(module: str, args: list[str], dsn: str):
    return subprocess.run(
        [sys.executable, "-m", PREFIX + module, *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": dsn},
        check=False,
    )


def success(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return json.loads(result.stdout)


def failure(result: subprocess.CompletedProcess[str], code: str):
    assert result.returncode == 2 and result.stdout == "", result.stdout + result.stderr
    assert json.loads(result.stderr)["code"] == code, result.stderr
    assert "Traceback" not in result.stderr and "postgresql://" not in result.stderr


def setup(tmp_path: Path, dsn: str):
    args = inputs(tmp_path)
    ctx = json.loads(Path(args[args.index("--context") + 1]).read_text())
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(ctx["scope"]))
    success(run("assertion_archive", ["init"], dsn))
    success(run("planned_execution_archive", ["init"], dsn))
    return args, scope


def test_actual_archive_restart_delete_export_and_legacy_reader(archive_dsn: str, tmp_path: Path):
    args, scope = setup(tmp_path, archive_dsn)
    original = Path(args[0]).read_bytes()
    first = success(run("execute_package", args + ["--archive"], archive_dsn))

    def repeat(_: int):
        return success(run("execute_package", args + ["--archive"], archive_dsn))

    with ThreadPoolExecutor(max_workers=4) as pool:
        repeats = list(pool.map(repeat, range(4)))
    receipt = first["archive_receipt"]
    key = receipt["execution_digest"]
    for again in repeats:
        assert again["archive_receipt"] == receipt
        assert again["retained_execution_receipt"] == first["retained_execution_receipt"]
        assert (
            again["execution_receipt"]["receipt_digest"]
            != first["execution_receipt"]["receipt_digest"]
        )
    assert first["execution_receipt"]["execution_digest"] == key
    assert len(first["transformations"]) == 5 and len(first["execution_receipt"]["entries"]) == 12
    assert all(x["status"] == "NOT_EXECUTED" for x in first["execution_receipt"]["entries"][5:])
    Path(args[0]).unlink()
    shown = success(
        run(
            "planned_execution_archive",
            ["show", "--scope", str(scope), "--execution-digest", key],
            archive_dsn,
        )
    )
    assert shown["retained_execution_receipt"] == first["retained_execution_receipt"]
    assert shown["assertion_batch"] == first["assertion_batch"]
    page = success(
        run(
            "planned_execution_archive",
            ["history", "--scope", str(scope), "--limit", "1"],
            archive_dsn,
        )
    )
    assert (
        page["receipts"] == [receipt]
        and page["has_more"] is False
        and page["next_after_sequence"] is None
    )
    output = tmp_path / "export.xlsx"
    cmd = ["content", "--scope", str(scope), "--execution-digest", key, "--output", str(output)]
    success(run("planned_execution_archive", cmd, archive_dsn))
    assert output.read_bytes() == original
    failure(
        run("planned_execution_archive", cmd, archive_dsn), "pil.input.archive_contract_invalid"
    )
    old = success(
        run(
            "assertion_archive",
            ["show", "--scope", str(scope), "--snapshot-id", receipt["snapshot_id"]],
            archive_dsn,
        )
    )
    assert old["assertion_batch"] == first["assertion_batch"]
    foreign = json.loads(scope.read_text())
    foreign["tenant_id"] = "foreign"
    scope.write_text(json.dumps(foreign))
    failure(
        run(
            "planned_execution_archive",
            ["show", "--scope", str(scope), "--execution-digest", key],
            archive_dsn,
        ),
        "pil.input.archive_not_found",
    )


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["unknown"],
        ["show"],
        ["history", "--scope", "missing", "--limit", "1.5"],
        ["history", "--scope", "missing", "--limit", "0"],
        ["history", "--scope", "missing", "--limit", "201"],
        ["history", "--scope", "missing", "--after-sequence", "-1"],
        ["show", "--scope", "missing", "--execution-digest", "A" * 64],
    ],
)
def test_bad_arguments_are_safe_json_before_storage(tmp_path: Path, args: list[str]):
    failure(run("planned_execution_archive", args, ""), "pil.input.archive_contract_invalid")


def test_runtime_and_capability_preflight_before_deleted_source(archive_dsn: str, tmp_path: Path):
    args = inputs(tmp_path)
    Path(args[0]).unlink()
    success(run("assertion_archive", ["init"], archive_dsn))
    failure(
        run("execute_package", args + ["--archive"], archive_dsn),
        "pil.infrastructure.archive_unavailable",
    )
    # A valid plan advertises an unavailable runtime; driver/configuration must not win admission.
    r = tmp_path / "registry.json"
    registry = json.loads(Path(args[args.index("--registry") + 1]).read_text())
    registry["implementations"][0]["implementation_id"] = "planning-only-capture"
    r.write_text(json.dumps(registry))
    args[args.index("--registry") + 1] = str(r)
    c = tmp_path / "config.toml"
    c.write_text(
        Path(args[args.index("--config") + 1])
        .read_text()
        .replace("local-file-capture", "planning-only-capture")
    )
    args[args.index("--config") + 1] = str(c)
    failure(run("execute_package", args + ["--archive"], ""), "pil.input.package_execution_invalid")


@pytest.mark.parametrize("mode", ["unicode", "large", "duplicate", "missing"])
def test_scope_validation_is_bounded_and_typed(archive_dsn: str, tmp_path: Path, mode: str):
    _, scope = setup(tmp_path, archive_dsn)
    if mode == "unicode":
        data = json.loads(scope.read_text())
        data["tenant_id"] = "bad\ud800"
        scope.write_text(json.dumps(data))
    elif mode == "large":
        scope.write_bytes(b" " * 32769)
    elif mode == "duplicate":
        scope.write_text('{"tenant_id":"a","tenant_id":"b"}')
    else:
        scope.unlink()
    failure(
        run("planned_execution_archive", ["history", "--scope", str(scope)], archive_dsn),
        "pil.input.archive_contract_invalid",
    )


def test_lost_ack_public_main_recovers_one_committed_result(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    from procurement_intelligence_lab.interfaces import execute_package

    args, scope = setup(tmp_path, archive_dsn)
    adapter = bootstrap.build_planned_execution_archive(archive_dsn)
    append = adapter.append

    def lost(*args: Any, **kwargs: Any):
        append(*args, **kwargs)
        raise ArchiveUnavailableError("archive acknowledgement unavailable")

    monkeypatch.setattr(adapter, "append", lost)

    def factory(dsn: str):
        return adapter

    monkeypatch.setattr(execute_package, "build_planned_execution_archive", factory)
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setattr(sys, "argv", ["execute_package", *args, "--archive"])
    assert execute_package.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == "pil.infrastructure.archive_unavailable"
    assert "rollback" not in captured.err
    Path(args[0]).unlink()
    page = success(
        run("planned_execution_archive", ["history", "--scope", str(scope)], archive_dsn)
    )
    assert len(page["receipts"]) == 1
    key = page["receipts"][0]["execution_digest"]
    assert (
        success(
            run(
                "planned_execution_archive",
                ["show", "--scope", str(scope), "--execution-digest", key],
                archive_dsn,
            )
        )["archive_receipt"]
        == page["receipts"][0]
    )


def test_corrupt_retention_is_not_public_success(archive_dsn: str, tmp_path: Path):
    args, scope = setup(tmp_path, archive_dsn)
    first = success(run("execute_package", args + ["--archive"], archive_dsn))
    key = first["archive_receipt"]["execution_digest"]
    with psycopg.connect(archive_dsn) as c:
        c.execute("ALTER TABLE pil_planned_executions DISABLE TRIGGER USER")
        c.execute("UPDATE pil_planned_executions SET payload_sha256='bad'")
    failure(
        run(
            "planned_execution_archive",
            ["show", "--scope", str(scope), "--execution-digest", key],
            archive_dsn,
        ),
        "pil.infrastructure.archive_integrity_invalid",
    )
