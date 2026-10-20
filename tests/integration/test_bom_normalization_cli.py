import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, workbook
from tests.integration.test_bom_stages_cli import CONTEXT, invoke

pytestmark = pytest.mark.integration


def run(source: Path, policy: Path, context: Path = CONTEXT):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.bom_stages",
            str(source),
            "--context",
            str(context),
            "--normalization-policy",
            str(policy),
        ],
        cwd=source.parent,
        text=True,
        capture_output=True,
        check=False,
    )


def policy_file(tmp_path: Path, **changes: object) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "profile": "bom-decimal@1",
                "quantity_unit": "dozen",
                "currency": "USD",
                "price_unit": "each",
                **changes,
            }
        )
    )
    return path


def test_opt_in_normalizes_with_full_evidence_and_fourth_transformation(tmp_path: Path) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    before = json.loads(invoke(path).stdout)
    policy = policy_file(tmp_path)
    result = run(path, policy)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["executed_stages"] == ["INGEST", "STRUCTURE", "MAP", "NORMALIZE"]
    for key in ("artifact", "structured_document", "mapped_document"):
        assert payload[key] == before[key]
    batch = payload["normalization"]
    observations = batch["observations"]
    quantity = next(x for x in observations if x["observation_key"] == "BOM!C7")
    assert quantity["value"] == "6.0" and quantity["unit"] == "each"
    assert quantity["source_field"]["raw_value"] == "0.5"
    assert quantity["source_field"]["evidence"]["cells"] == ["C"]
    assert quantity["source_field"]["evidence"]["artifact_id"] == payload["artifact"]["artifact_id"]
    assert quantity["effective_at"] == payload["artifact"]["source"]["observed_at"]
    assert quantity["scope"] == payload["artifact"]["source"]["scope"]
    assert quantity["provenance"] == batch["provenance"]
    event = payload["transformations"][3]
    assert event["parent_event_ids"] == [before["transformations"][2]["event_id"]]
    assert event["output_ids"] == [batch["batch_id"], *[x["observation_id"] for x in observations]]
    assert payload["normalization_policy"]["quantity_unit"] == "dozen"
    assert run(path, policy).stdout == result.stdout
    changed = json.loads(run(path, policy_file(tmp_path, currency="EUR")).stdout)
    assert changed["normalization"]["batch_id"] != batch["batch_id"]
    assert changed["mapped_document"] == before["mapped_document"]


def test_header_only_has_real_empty_receipt_and_no_invented_observation(tmp_path: Path) -> None:
    result = run(workbook(tmp_path / "empty.xlsx", HEADER), policy_file(tmp_path))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["normalization"]["observations"] == []
    assert payload["transformations"][3]["output_ids"] == [payload["normalization"]["batch_id"]]


@pytest.mark.parametrize(
    "change",
    [
        "absent",
        "malformed",
        "duplicate",
        "missing_unit",
        "currency",
        "unknown",
        "profile",
        "numeric",
        "unit_type",
    ],
)
def test_policy_and_value_failures_are_typed_without_partial_stdout(
    tmp_path: Path, change: str
) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    policy = policy_file(tmp_path)
    if change == "absent":
        policy.unlink()
    elif change == "malformed":
        policy.write_text("{")
    elif change == "duplicate":
        policy.write_text('{"currency":"USD","currency":"EUR"}')
    elif change == "numeric":
        workbook(path, HEADER + ROW.replace("<v>0.5</v>", "<v>1,000</v>"))
    else:
        data = json.loads(policy.read_text())
        if change == "missing_unit":
            del data["quantity_unit"]
        elif change == "currency":
            data["currency"] = "usd"
        elif change == "unknown":
            data["fallback"] = 0
        elif change == "profile":
            data["profile"] = "other"
        elif change == "unit_type":
            data["price_unit"] = []
        policy.write_text(json.dumps(data))
    result = run(path, policy)
    assert result.returncode == 2 and not result.stdout
    expected = (
        "pil.interpretation.normalization_invalid"
        if change == "numeric"
        else "pil.input.normalization_policy_invalid"
    )
    assert json.loads(result.stderr)["code"] == expected


def test_default_path_still_retains_invalid_numeric_text_without_normalization(
    tmp_path: Path,
) -> None:
    result = invoke(
        workbook(tmp_path / "raw.xlsx", HEADER + ROW.replace("<v>0.5</v>", "<v>unknown</v>"))
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["executed_stages"] == ["INGEST", "STRUCTURE", "MAP"]
    assert "normalization" not in payload
