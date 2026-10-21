import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, workbook

pytestmark = pytest.mark.integration
ROOT = Path(__file__).parents[2]


def inputs(tmp_path: Path, rows: str = HEADER + ROW):
    source = workbook(tmp_path / "source.xlsx", rows)
    manifest = tmp_path / "manifest.json"
    compiled = subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.domain_package"],
        text=True,
        capture_output=True,
        check=True,
    )
    manifest.write_text(compiled.stdout)
    context = tmp_path / "context.json"
    data = json.loads((ROOT / "tests/fixtures/bom-stages/context.json").read_text())
    data["code_revision"] = "test-revision"
    context.write_text(json.dumps(data))
    return [
        str(source),
        "--manifest",
        str(manifest),
        "--registry",
        str(ROOT / "tests/fixtures/execution/procurement-registry.json"),
        "--config",
        str(ROOT / "tests/fixtures/execution/procurement-config.toml"),
        "--stop-after",
        "ASSERT",
        "--context",
        str(context),
        "--normalization-policy",
        str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
    ]


def run(args: list[str]):
    return subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.execute_package", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_actual_cli_compiles_plan_and_executes_five_real_stages(tmp_path: Path):
    args = inputs(tmp_path, HEADER + ROW + ROW.replace("7", "8"))
    done = run(args)
    assert done.returncode == 0, done.stderr
    body = json.loads(done.stdout)
    r = body["execution_receipt"]
    assert body["executed_stages"] == ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT"]
    assert len(body["transformations"]) == 5 and len(r["entries"]) == 12
    assert r["requested_prefix_complete"] is True and r["package_execution_complete"] is False
    assert all(
        e["status"] == "NOT_EXECUTED" and e["event_id"] is None and e["output_ids"] == []
        for e in r["entries"][5:]
    )
    assert r["context"]["workflow_name"] == "planned-source-assertion-prefix"
    assert len(r["resolved_references"]) == 3
    claims = body["assertion_batch"]["claims"]
    assert [c["value"] for c in claims if c["predicate"] == "has_sku"] == ["GPU-A", "GPU-A"]
    assert len({c["assertion_id"] for c in claims}) == 8
    again = run(args)
    assert again.returncode == 0
    other = json.loads(again.stdout)["execution_receipt"]
    assert other["execution_digest"] == r["execution_digest"]
    assert other["receipt_digest"] != r["receipt_digest"]


@pytest.mark.parametrize(
    "mode",
    [
        "unknown-arg",
        "boundary",
        "registry",
        "context-duplicate",
        "context-extra",
        "context-unicode",
        "context-deep",
        "context-big",
        "policy-invalid",
        "manifest-invalid",
        "config-mismatch",
        "registry-big",
    ],
)
def test_actual_cli_failures_are_typed_without_source_io(tmp_path: Path, mode: str):
    args = inputs(tmp_path)
    Path(args[0]).unlink()
    if mode == "unknown-arg":
        args += ["--unknown", "sensitive-value"]
    elif mode == "boundary":
        args[args.index("--stop-after") + 1] = "DETECT"
    elif mode == "registry":
        p = tmp_path / "registry.json"
        x = json.loads(Path(args[args.index("--registry") + 1]).read_text())
        x["implementations"][0]["implementation_id"] = "unavailable"
        p.write_text(json.dumps(x))
        args[args.index("--registry") + 1] = str(p)
    elif mode.startswith("context-"):
        p = Path(args[args.index("--context") + 1])
        x = json.loads(p.read_text())
        if mode == "context-duplicate":
            p.write_text('{"scope":{},"scope":{}}')
        elif mode == "context-extra":
            x["unknown"] = "value"
            p.write_text(json.dumps(x))
        elif mode == "context-unicode":
            x["run_id"] = "bad\ud800"
            p.write_text(json.dumps(x))
        elif mode == "context-deep":
            p.write_text("[" * 1100 + "]" * 1100)
        else:
            p.write_bytes(b" " * 32769)
    elif mode == "policy-invalid":
        p = tmp_path / "policy.json"
        p.write_text('{"currency":NaN}')
        args[args.index("--normalization-policy") + 1] = str(p)
    elif mode == "manifest-invalid":
        Path(args[args.index("--manifest") + 1]).write_text("{}")
    elif mode == "config-mismatch":
        p = tmp_path / "config.toml"
        p.write_text(
            Path(args[args.index("--config") + 1])
            .read_text()
            .replace("local-file-capture", "unavailable")
        )
        args[args.index("--config") + 1] = str(p)
    else:
        p = tmp_path / "big.json"
        p.write_bytes(b" " * (1048576 + 1))
        args[args.index("--registry") + 1] = str(p)
    done = run(args)
    assert done.returncode == 2 and done.stdout == "", done.stdout + done.stderr
    error = json.loads(done.stderr)
    expected = (
        "pil.input.package_planning_invalid"
        if mode in ("registry", "manifest-invalid", "config-mismatch")
        else "pil.input.package_execution_invalid"
    )
    assert error["code"] == expected, done.stderr
    assert error["category"] in ("input", "interpretation")
    assert "Traceback" not in done.stderr and "sensitive-value" not in done.stderr
    assert error["code"] != "pil.infrastructure.artifact_source_unavailable"


def test_actual_cli_empty_source_is_positive_empty_batch(tmp_path: Path):
    done = run(inputs(tmp_path, HEADER))
    assert done.returncode == 0, done.stderr
    body = json.loads(done.stdout)
    assert body["assertion_batch"]["claims"] == []
    assert body["normalization"]["observations"] == []
    assert body["execution_receipt"]["entries"][4]["output_ids"] == [
        body["assertion_batch"]["batch_id"]
    ]


def test_actual_valid_plan_with_unregistered_executor_fails_before_source(tmp_path: Path):
    args = inputs(tmp_path)
    Path(args[0]).unlink()
    registry = tmp_path / "registry.json"
    data = json.loads(Path(args[args.index("--registry") + 1]).read_text())
    data["implementations"][0]["implementation_id"] = "planning-only-capture"
    registry.write_text(json.dumps(data))
    args[args.index("--registry") + 1] = str(registry)
    config = tmp_path / "config.toml"
    config.write_text(
        Path(args[args.index("--config") + 1])
        .read_text()
        .replace("local-file-capture", "planning-only-capture")
    )
    args[args.index("--config") + 1] = str(config)
    plan = subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.plan_package", *args[1:7]],
        capture_output=True,
        text=True,
        check=False,
    )
    assert plan.returncode == 0, plan.stderr
    done = run(args)
    assert done.returncode == 2 and done.stdout == ""
    assert json.loads(done.stderr)["code"] == "pil.input.package_execution_invalid"


def test_actual_neutral_prefix_is_rejected_without_source_read(tmp_path: Path):
    import re

    args = inputs(tmp_path)
    Path(args[0]).unlink()
    m = Path(args[args.index("--manifest") + 1])
    data = json.loads(m.read_text())
    b = data["stages"][1]
    b.update(
        mode="PASSTHROUGH",
        requirements=[],
        neutral_semantics=None,
        output_contract_verified=True,
        eval_suite_ref=None,
    )
    m.write_text(json.dumps(data))
    config = tmp_path / "config.toml"
    config.write_text(
        re.sub(
            r'(?s)\[\[selections\]\]\nstage = "STRUCTURE".*?(?=\[\[selections\]\]|\Z)',
            "",
            Path(args[args.index("--config") + 1]).read_text(),
        )
    )
    args[args.index("--config") + 1] = str(config)
    plan = subprocess.run(
        [sys.executable, "-m", "procurement_intelligence_lab.interfaces.plan_package", *args[1:7]],
        capture_output=True,
        text=True,
        check=False,
    )
    assert plan.returncode == 0, plan.stderr
    done = run(args)
    assert done.returncode == 2 and done.stdout == ""
    assert json.loads(done.stderr)["code"] == "pil.input.package_execution_invalid"
