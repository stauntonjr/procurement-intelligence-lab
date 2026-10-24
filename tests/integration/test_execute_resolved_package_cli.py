"""Actual six-stage process with explicit deployment inputs and early admission."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.bom_stage_fixtures import HEADER, ROW
from tests.integration.test_execute_package_cli import ROOT
from tests.integration.test_execute_package_cli import inputs as prefix_inputs

pytestmark = pytest.mark.integration


def inputs(tmp_path: Path, rows: str = HEADER + ROW):
    args = prefix_inputs(tmp_path, rows)
    for flag, name in (
        ("registry", "procurement-registry.json"),
        ("config", "procurement-config.toml"),
    ):
        path = tmp_path / name
        path.write_bytes((ROOT / "tests/fixtures/resolved-execution" / name).read_bytes())
        args[args.index("--" + flag) + 1] = str(path)
    args[args.index("--stop-after") + 1] = "RESOLVE"
    for flag in ("resolution-policy", "candidate-snapshot"):
        path = tmp_path / (flag + ".json")
        path.write_bytes((ROOT / "tests/fixtures/resolved-execution" / path.name).read_bytes())
        args += ["--" + flag, str(path)]
    return args


def run(args: list[str]):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.execute_resolved_package",
            *args,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_actual_six_stages_preserve_duplicate_rows_and_evidence(tmp_path: Path):
    args = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8"))
    done = run(args)
    assert done.returncode == 0, done.stderr
    body = json.loads(done.stdout)
    assert len(body["transformations"]) == 6
    receipt = body["execution_receipt"]
    assert len(receipt["entries"]) == 12
    assert [e["status"] for e in receipt["entries"]] == ["SUCCEEDED"] * 6 + ["NOT_EXECUTED"] * 6
    assert receipt["package_execution_complete"] is False
    outcomes = body["resolution"]["outcomes"]
    assert len(outcomes) == 2 and len({x["mention_id"] for x in outcomes}) == 2
    assert all(x["matched_keys"] == ["GPU-A"] and x["status"] == "resolved" for x in outcomes)
    assert [x["evidence"][0]["evidence"]["location"]["row"] for x in outcomes] == [7, 8]
    assert len(body["resolution"]["canonicalized_assertions"]) == 8
    assert not body["resolution"]["unlinked_assertion_ids"]


@pytest.mark.parametrize(
    "keys,sku,status",
    [
        ((), "GPU-A", "unresolved"),
        (("GPU A", "GPU-A"), "GPU-A", "unresolved"),
        (("GPU-A",), "---", "unresolved"),
        (("GPU-A",), "gpu a", "resolved"),
        ((), "", None),
    ],
)
def test_actual_abstentions_and_missing_sku(
    tmp_path: Path, keys: tuple[str, ...], sku: str, status: str | None
):
    args = inputs(tmp_path, HEADER + ROW.replace("GPU-A", sku))
    p = Path(args[args.index("--candidate-snapshot") + 1])
    c = json.loads(p.read_text())
    c["keys"] = keys
    p.write_text(json.dumps(c))
    done = run(args)
    assert done.returncode == 0, done.stderr
    o = json.loads(done.stdout)["resolution"]
    assert [x["status"] for x in o["outcomes"]] == ([] if status is None else [status])
    assert bool(o["canonicalized_assertions"]) == (status == "resolved")
    assert bool(o["unlinked_assertion_ids"]) == (status != "resolved")


@pytest.mark.parametrize(
    "mode",
    [
        "duplicate",
        "unknown",
        "scope",
        "namespace",
        "future",
        "257",
        "unicode",
        "too-big",
        "policy",
        "stop",
        "descriptor",
        "settings",
        "pin",
        "missing",
    ],
)
def test_admission_failures_precede_absent_source_and_storage(tmp_path: Path, mode: str):
    args = inputs(tmp_path)
    Path(args[0]).unlink()
    p = Path(args[args.index("--candidate-snapshot") + 1])
    c: dict[str, Any] = json.loads(p.read_text())
    if mode == "duplicate":
        p.write_text('{"keys":[],"keys":[]}')
    elif mode == "unknown":
        c["unknown"] = "sensitive-value"
    elif mode == "scope":
        c["scope"]["version"] = "foreign"
    elif mode == "namespace":
        c["identifier_namespace"] = "supplier_name"
    elif mode == "future":
        c["effective_at"] = "2030-01-01T00:00:00Z"
    elif mode == "257":
        c["keys"] = [str(i) for i in range(257)]
    elif mode == "unicode":
        c["keys"] = ["bad\ud800"]
    elif mode == "too-big":
        p.write_bytes(b" " * 32769)
    elif mode == "policy":
        Path(args[args.index("--resolution-policy") + 1]).write_text('{"profile":null}')
    elif mode == "stop":
        args[args.index("--stop-after") + 1] = "ASSERT"
    elif mode == "descriptor":
        rp = Path(args[args.index("--registry") + 1])
        r = json.loads(rp.read_text())
        r["implementations"][5]["implementation_version"] = "2"
        rp.write_text(json.dumps(r))
    elif mode == "settings":
        cp = Path(args[args.index("--config") + 1])
        cp.write_text(
            cp.read_text().replace(
                'implementation_id = "bom-normalized-exact-resolve"\nconfig_schema_version = "1.0"\nsettings = {}',
                'implementation_id = "bom-normalized-exact-resolve"\nconfig_schema_version = "1.0"\nsettings = {unknown="sensitive-value"}',
            )
        )
    elif mode == "pin":
        cp = Path(args[args.index("--context") + 1])
        x = json.loads(cp.read_text())
        x["code_revision"] = "foreign"
        cp.write_text(json.dumps(x))
    elif mode == "missing":
        p.unlink()
    if mode in ("unknown", "scope", "namespace", "future", "257", "unicode"):
        p.write_text(json.dumps(c))
    done = run(args + ["--archive"])
    assert done.returncode == 2 and done.stdout == "", done.stderr
    error = json.loads(done.stderr)
    assert error["code"] in (
        "pil.input.package_execution_invalid",
        "pil.input.package_planning_invalid",
    ), done.stderr
    assert "Traceback" not in done.stderr and "sensitive-value" not in done.stderr


def test_empty_and_256_keys_and_offset_equal_time(tmp_path: Path):
    args = inputs(tmp_path, HEADER)
    p = Path(args[args.index("--candidate-snapshot") + 1])
    c = json.loads(p.read_text())
    c["keys"] = [str(i) for i in range(256)]
    c["effective_at"] = "2026-10-18T20:00:00-04:00"
    p.write_text(json.dumps(c))
    done = run(args)
    assert done.returncode == 0, done.stderr
    body = json.loads(done.stdout)
    assert body["resolution"]["outcomes"] == []
    assert body["resolution"]["candidates"]["effective_at"] == c["effective_at"]


@pytest.mark.parametrize("quantity", ["0", "-2", "0.5", None])
def test_resolution_preserves_numeric_source_values(tmp_path: Path, quantity: str | None):
    rows = HEADER + (
        ROW.replace('<c r="C7"><v>0.5</v></c>', "")
        if quantity is None
        else ROW.replace("<v>0.5</v>", "<v>" + quantity + "</v>")
    )
    done = run(inputs(tmp_path, rows))
    assert done.returncode == 0, done.stderr
    body = json.loads(done.stdout)
    claims = body["assertion_batch"]["claims"]
    values = [c["value"] for c in claims if c["predicate"] == "has_quantity"]
    assert values == [quantity]
    if quantity is None:
        assert next(c for c in claims if c["predicate"] == "has_quantity")["status"] == "unresolved"
    assert body["resolution"]["outcomes"][0]["canonical_key"] == "GPU-A"


def test_help_and_missing_required_inputs():
    help_result = run(["--help"])
    assert help_result.returncode == 0 and "--candidate-snapshot" in help_result.stdout
    missing = run([])
    assert (
        missing.returncode == 2
        and json.loads(missing.stderr)["code"] == "pil.input.package_execution_invalid"
    )
