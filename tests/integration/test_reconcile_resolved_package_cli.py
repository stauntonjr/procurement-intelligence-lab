"""Actual CLI reconciles already-archived producers, preserving all evidence and abstentions."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.bom_stage_fixtures import HEADER, ROW
from tests.integration.test_planned_execution_archive_cli import failure, run, success
from tests.reconciliation_public_fixtures import inputs

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "rows,expected,governing",
    [
        ((HEADER,), None, 0),
        ((HEADER + ROW,), "0.5", 1),
        ((HEADER + ROW, HEADER + ROW.replace("100.50", "101.50")), "0.5", 2),
        ((HEADER + ROW, HEADER + ROW.replace("<v>0.5</v>", "<v>2.5</v>")), None, 0),
        ((HEADER + ROW.replace("<v>0.5</v>", "<v>0</v>"),), "0", 1),
    ],
)
def test_real_operation_with_governed_shared_conflict_empty_zero(
    archive_dsn: str, tmp_path: Path, rows: tuple[str, ...], expected: str | None, governing: int
):
    args, _, ps = inputs(tmp_path, archive_dsn, rows)
    body = success(run("reconcile_resolved_package", args, archive_dsn))
    r = body["current_operation"]
    assert len(r["entries"]) == 12 and [e["status"] for e in r["entries"]].count("SUCCEEDED") == 1
    assert r["entries"][6]["stage"] == "RECONCILE" and not r["package_execution_complete"]
    assert len(body["recorded_producers"]) == len(ps)
    if expected is None:
        assert r["states"] == []
    else:
        assert r["states"][0]["attributes"][0]["value"] == expected
        assert len(r["decisions"][0]["governing"]) == governing
        assert r["states"][0]["freshness"] == "unknown"
        assert r["states"][0]["scope"]["version"] != "1"
    for p in body["recorded_producers"]:
        assert [e["status"] for e in p["execution_receipt"]["entries"]].count("SUCCEEDED") == 6


@pytest.mark.parametrize(
    "mode",
    [
        "duplicate",
        "unknown",
        "missing",
        "big",
        "unicode",
        "policy",
        "descriptor",
        "settings",
        "code",
        "context",
        "nine",
        "digest",
        "authority-set",
    ],
)
def test_public_invalid_metadata_precedes_storage(archive_dsn: str, tmp_path: Path, mode: str):
    args, _, _ = inputs(tmp_path, archive_dsn)
    path = Path(args[args.index("--authority") + 1])
    wire: dict[str, Any] = json.loads(path.read_text())
    if mode == "duplicate":
        path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
    elif mode == "unknown":
        wire["producers"][0]["private"] = "sensitive-value"
        path.write_text(json.dumps(wire))
    elif mode == "missing":
        del wire["producers"][0]["approval"]
        path.write_text(json.dumps(wire))
    elif mode == "big":
        path.write_bytes(b" " * 65537)
    elif mode == "unicode":
        wire["producers"][0]["revision_id"] = "bad\ud800"
        path.write_text(json.dumps(wire))
    elif mode == "policy":
        Path(args[args.index("--governing-policy") + 1]).write_text("{}")
    elif mode == "descriptor":
        p = Path(args[args.index("--registry") + 1])
        r = json.loads(p.read_text())
        r["implementations"][6]["implementation_version"] = "2"
        p.write_text(json.dumps(r))
    elif mode == "settings":
        p = Path(args[args.index("--config") + 1])
        p.write_text(
            p.read_text().replace(
                'implementation_id = "bom-governed-required-quantity"\nconfig_schema_version = "1.0"\nsettings = {}',
                'implementation_id = "bom-governed-required-quantity"\nconfig_schema_version = "1.0"\nsettings = {unknown="sensitive-value"}',
            )
        )
    elif mode in ("code", "context"):
        p = Path(args[args.index("--context") + 1])
        c = json.loads(p.read_text())
        c["code_revision" if mode == "code" else "unknown"] = "sensitive-value"
        p.write_text(json.dumps(c))
    elif mode == "nine":
        args += ["--producer-digest", "0" * 64] * 9
    elif mode == "digest":
        args[args.index("--producer-digest") + 1] = "bad"
    else:
        wire["producers"][0]["execution_digest"] = "0" * 64
        path.write_text(json.dumps(wire))
    result = run(
        "reconcile_resolved_package",
        args + ["--archive"],
        "postgresql://invalid:1/must-not-connect",
    )
    assert result.returncode == 2 and not result.stdout
    error = json.loads(result.stderr)
    assert error["code"] in (
        "pil.input.package_execution_invalid",
        "pil.input.package_planning_invalid",
    )
    assert (
        "Traceback" not in result.stderr
        and "sensitive-value" not in result.stderr
        and "postgresql://" not in result.stderr
    )


def test_public_raw_format_retry_first_receipt(archive_dsn: str, tmp_path: Path):
    args, _, _ = inputs(tmp_path, archive_dsn)
    success(run("reconciliation_archive", ["init"], archive_dsn))
    first = success(run("reconcile_resolved_package", args + ["--archive"], archive_dsn))
    p = Path(args[args.index("--authority") + 1])
    p.write_text(json.dumps(json.loads(p.read_text()), indent=2))
    again = success(run("reconcile_resolved_package", args + ["--archive"], archive_dsn))
    assert (
        again["current_operation"]["execution_digest"]
        == first["current_operation"]["execution_digest"]
    )
    assert again["archive_receipt"] == first["archive_receipt"]
    assert (
        again["current_operation"]["authority"]["raw_sha256"]
        != first["current_operation"]["authority"]["raw_sha256"]
    )
    assert again["first_retained_operation"] == first["first_retained_operation"]


def test_public_identical_bytes_and_omitted_successor_fail_before_stage(
    archive_dsn: str, tmp_path: Path
):
    args, _, _ = inputs(tmp_path, archive_dsn, (HEADER + ROW, HEADER))
    p = Path(args[args.index("--authority") + 1])
    wire = json.loads(p.read_text())
    wire["producers"][1]["supersedes_revision_ids"] = ["r0"]
    p.write_text(json.dumps(wire))
    result = run("reconcile_resolved_package", args, archive_dsn)
    failure(result, "pil.input.reconciliation_input_unsupported")
    assert len(json.loads(result.stderr)["producer_recovery"]) == 2


def test_public_identical_content_has_no_extra_authority(archive_dsn: str, tmp_path: Path):
    args, _, ps = inputs(tmp_path, archive_dsn, (HEADER + ROW, HEADER + ROW), identical=True)
    assert ps[0]["artifact"]["content_hash"] == ps[1]["artifact"]["content_hash"]
    result = run("reconcile_resolved_package", args, archive_dsn)
    failure(result, "pil.input.reconciliation_input_unsupported")
    assert len(json.loads(result.stderr)["producer_recovery"]) == 2


def test_public_nonempty_successor_omission(archive_dsn: str, tmp_path: Path):
    two = HEADER + ROW + ROW.replace("7", "8").replace("GPU-A", "CPU-A")
    args, _, _ = inputs(
        tmp_path, archive_dsn, (two, HEADER + ROW), candidate_keys=("GPU-A", "CPU-A")
    )
    p = Path(args[args.index("--authority") + 1])
    wire = json.loads(p.read_text())
    wire["producers"][1]["supersedes_revision_ids"] = ["r0"]
    p.write_text(json.dumps(wire))
    failure(
        run("reconcile_resolved_package", args, archive_dsn),
        "pil.input.reconciliation_input_unsupported",
    )


@pytest.mark.parametrize("case", ["null", "future", "expired", "start", "offset", "historical"])
def test_public_temporal_endpoints_offsets_and_ingestion(
    archive_dsn: str, tmp_path: Path, case: str
):
    args, _, _ = inputs(tmp_path, archive_dsn)
    p = Path(args[args.index("--authority") + 1])
    w = json.loads(p.read_text())
    r = w["producers"][0]
    if case == "null":
        r["approval"] = None
    elif case == "future":
        r["approval"]["approved_at"] = "2026-10-19T00:00:01Z"
    elif case == "expired":
        r["effective_from"] = "2026-10-18T00:00:00Z"
        r["effective_until"] = "2026-10-19T00:00:00Z"
    elif case == "offset":
        r["approval"]["approved_at"] = "2026-10-18T20:00:00-04:00"
        r["effective_from"] = "2026-10-18T20:00:00-04:00"
    elif case == "historical":
        r["approval"]["approved_at"] = r["effective_from"] = "2026-10-18T00:00:00Z"
        args[args.index("--as-of") + 1] = "2026-10-18T00:00:00Z"
    p.write_text(json.dumps(w))
    out = success(run("reconcile_resolved_package", args, archive_dsn))["current_operation"]
    assert bool(out["states"]) == (case not in ("null", "future", "expired"))
    if case == "future":
        assert (
            out["domain_audit"]["items"][0]["decision"]["dispositions"][0][1]
            == "approval_after_as_of"
        )
    if case == "offset":
        assert "-04:00" in json.dumps(out["domain_audit"])


def test_public_bounds_and_catalog_mismatch(archive_dsn: str, tmp_path: Path):
    args, _, _ = inputs(tmp_path, archive_dsn, padding=4 * 1024 * 1024)
    result = run("reconcile_resolved_package", args, archive_dsn)
    failure(result, "pil.input.reconciliation_input_unsupported")
    assert "aggregate" in json.loads(result.stderr)["message"]
    # Use small producers so the byte guard cannot mask catalog validation.
    small = tmp_path / "small"
    small.mkdir()
    args, _, _ = inputs(small, archive_dsn)
    # A separate actual producer uses a different semantic catalog, even with the same matched key.
    from tests.integration.test_execute_resolved_package_cli import inputs as resolved_inputs

    folder = tmp_path / "other-catalog"
    folder.mkdir()
    source_args = resolved_inputs(folder, HEADER + ROW.replace("100.50", "101.50"))
    path = Path(source_args[source_args.index("--candidate-snapshot") + 1])
    catalog = json.loads(path.read_text())
    catalog["catalog_revision"] = "different"
    path.write_text(json.dumps(catalog))
    q = success(run("execute_resolved_package", source_args + ["--archive"], archive_dsn))
    old = Path(args[args.index("--authority") + 1])
    w = json.loads(old.read_text())
    record = dict(
        w["producers"][0],
        execution_digest=q["execution_receipt"]["execution_digest"],
        artifact_id=q["artifact"]["artifact_id"],
        content_hash=q["artifact"]["content_hash"],
        revision_id="different",
    )
    w["producers"].append(record)
    old.write_text(json.dumps(w))
    args += ["--producer-digest", record["execution_digest"]]
    result = run("reconcile_resolved_package", args, archive_dsn)
    failure(result, "pil.input.package_execution_invalid")
    assert len(json.loads(result.stderr)["producer_recovery"]) == 2


def test_public_exact_authority_byte_bound(archive_dsn: str, tmp_path: Path):
    args, _, _ = inputs(tmp_path, archive_dsn)
    path = Path(args[args.index("--authority") + 1])
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (65536 - len(raw)))
    result = success(run("reconcile_resolved_package", args, archive_dsn))
    assert result["current_operation"]["states"]
    path.write_bytes(path.read_bytes() + b" ")
    failure(
        run("reconcile_resolved_package", args, archive_dsn), "pil.input.package_execution_invalid"
    )


@pytest.mark.parametrize("case", ["negative", "missing", "repeated", "unresolved"])
def test_public_unsupported_item_rows(archive_dsn: str, tmp_path: Path, case: str):
    row = HEADER + ROW
    if case == "negative":
        row = row.replace("<v>0.5</v>", "<v>-0.5</v>")
    elif case == "missing":
        row = row.replace("<v>0.5</v>", "<v></v>")
    elif case == "repeated":
        row += ROW.replace("7", "8")
    else:
        row = row.replace("GPU-A", "UNKNOWN")
    args, _, _ = inputs(tmp_path, archive_dsn, (row,))
    failure(
        run("reconcile_resolved_package", args, archive_dsn),
        "pil.input.reconciliation_input_unsupported",
    )


@pytest.mark.parametrize("archive", [False, True])
def test_public_wrong_domain_rejects_before_unavailable_storage(
    archive_dsn: str, tmp_path: Path, archive: bool
):
    args, _, _ = inputs(tmp_path, archive_dsn)
    path = Path(args[args.index("--manifest") + 1])
    value = json.loads(path.read_text())
    value["domain"]["id"] = "inventory"
    path.write_text(json.dumps(value))
    result = run(
        "reconcile_resolved_package",
        args + (["--archive"] if archive else []),
        "postgresql://invalid:1/must-not-connect",
    )
    failure(result, "pil.input.package_execution_invalid")
    assert len(json.loads(result.stderr)["producer_recovery"]) == 1
