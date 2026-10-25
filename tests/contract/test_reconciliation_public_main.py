"""Real public main functions retain/recover data and reject deployment before I/O."""

import json
import sys
from pathlib import Path
from typing import Any, NoReturn

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.interfaces import (
    reconcile_resolved_package,
    reconciliation_archive,
)
from tests.reconciliation_public_fixtures import inputs

pytestmark = pytest.mark.contract


def forbidden(*args: Any, **kwargs: Any) -> NoReturn:
    raise AssertionError("invalid deployment reached storage or executor construction")


def invoke(
    module: Any,
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    code = module.main()
    out = capsys.readouterr()
    if code == 0:
        assert not out.err
        return json.loads(out.out)
    assert code == 2 and not out.out and "Traceback" not in out.err
    return json.loads(out.err)


@pytest.mark.parametrize("archive", [False, True])
@pytest.mark.parametrize("variant", ["domain", "profile", "profile-version"])
def test_invalid_deployment_never_constructs_storage_or_executor(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    archive: bool,
    variant: str,
):
    args, _, _ = inputs(tmp_path, archive_dsn)
    manifest = Path(args[args.index("--manifest") + 1])
    wire = json.loads(manifest.read_text())
    config = Path(args[args.index("--config") + 1])
    if variant == "domain":
        wire["domain"]["id"] = "inventory"
    elif variant == "profile":
        wire["source_profile"]["id"] = "other"
        config.write_text(
            config.read_text().replace(
                'source_profile = "retained-resolved-required-quantity"', 'source_profile = "other"'
            )
        )
    else:
        wire["source_profile"]["version"] = "2.0.0"
        config.write_text(
            config.read_text().replace(
                'source_profile_version = "1.0.0"', 'source_profile_version = "2.0.0"'
            )
        )
    manifest.write_text(json.dumps(wire))
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", "postgresql://invalid:1/must-not-connect")
    monkeypatch.setattr(bootstrap, "build_resolved_execution_archive_reader", forbidden)
    monkeypatch.setattr(bootstrap, "build_reconciliation_archive", forbidden)
    from procurement_intelligence_lab.adapters import package_reconciliation_executor

    monkeypatch.setattr(package_reconciliation_executor, "PackageReconciliationExecutor", forbidden)
    result = invoke(
        reconcile_resolved_package, args + (["--archive"] if archive else []), monkeypatch, capsys
    )
    assert result["code"] == "pil.input.package_execution_invalid"


def test_public_main_execute_archive_and_source_free_recovery(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    args, scope, _ = inputs(tmp_path, archive_dsn)
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    fresh = invoke(reconcile_resolved_package, args, monkeypatch, capsys)
    assert fresh["current_operation"]["states"][0]["attributes"][0]["value"] == "0.5"
    invoke(reconciliation_archive, ["init"], monkeypatch, capsys)
    first = invoke(reconcile_resolved_package, args + ["--archive"], monkeypatch, capsys)
    for flag in (
        "--manifest",
        "--context",
        "--config",
        "--registry",
        "--governing-policy",
        "--authority",
    ):
        Path(args[args.index(flag) + 1]).unlink()
    source = tmp_path / "producer-0/source.xlsx"
    source.unlink()
    key = first["current_operation"]["execution_digest"]
    common = ["--scope", str(scope), "--execution-digest", key]
    shown = invoke(reconciliation_archive, ["show", *common], monkeypatch, capsys)
    assert shown["current_operation"] == first["first_retained_operation"]
    page = invoke(reconciliation_archive, ["history", "--scope", str(scope)], monkeypatch, capsys)
    assert page["receipts"] == [first["archive_receipt"]]
    manifest = invoke(reconciliation_archive, ["content-manifest", *common], monkeypatch, capsys)
    assert manifest["original_source_bytes_included"] is False
    out = tmp_path / "export.json"
    invoke(reconciliation_archive, ["export", *common, "--output", str(out)], monkeypatch, capsys)
    assert out.is_file()
    error = invoke(
        reconciliation_archive, ["export", *common, "--output", str(out)], monkeypatch, capsys
    )
    assert error["code"] == "pil.input.archive_contract_invalid"


def test_public_main_malformed_arguments_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    assert (
        invoke(reconcile_resolved_package, [], monkeypatch, capsys)["code"]
        == "pil.input.package_execution_invalid"
    )
    assert (
        invoke(reconciliation_archive, [], monkeypatch, capsys)["code"]
        == "pil.input.archive_contract_invalid"
    )
