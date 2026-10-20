import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, workbook
from tests.integration.test_bom_normalization_cli import policy_file, run
from tests.integration.test_bom_stages_cli import CONTEXT

pytestmark = pytest.mark.integration


def invoke_assertions(path: Path, policy: Path | None = None) -> subprocess.CompletedProcess[str]:
    argv = [
        sys.executable,
        "-m",
        "procurement_intelligence_lab.interfaces.bom_stages",
        str(path),
        "--context",
        str(CONTEXT),
        "--assertions",
    ]
    if policy is not None:
        argv.extend(["--normalization-policy", str(policy)])
    return subprocess.run(argv, cwd=path.parent, text=True, capture_output=True, check=False)


def test_cli_claims_trace_to_cells_and_preserve_four_stage_output(tmp_path: Path) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    policy = policy_file(tmp_path)
    before = json.loads(run(path, policy).stdout)
    result = invoke_assertions(path, policy)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    for key in ("normalization", "mapped_document", "structured_document", "artifact"):
        assert before[key] == payload[key]
    assert len(payload["transformations"]) == 5
    claims = payload["assertion_batch"]["claims"]
    quantity = next(x for x in claims if x["predicate"] == "has_quantity")
    assert quantity["value"] == "6.0" and quantity["raw_value"] == "0.5"
    assert quantity["evidence"]["cells"] == ["C"]
    assert quantity["trace"]["artifact_id"] == payload["artifact"]["artifact_id"]
    assert quantity["immutable_content_version"] == payload["artifact"]["content_hash"]
    assert quantity["trace"]["normalization_event_id"] == payload["transformations"][3]["event_id"]
    assert quantity["trace"]["assertion_event_id"] == payload["transformations"][4]["event_id"]
    missing = next(x for x in claims if x["predicate"] == "has_description")
    assert missing["value"] is None and missing["status"] == "unresolved" and missing["diagnostic"]
    assert invoke_assertions(path, policy).stdout == result.stdout


def test_cli_requires_policy_and_empty_is_a_receipt(tmp_path: Path) -> None:
    path = workbook(tmp_path / "empty.xlsx", HEADER)
    result = invoke_assertions(path)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.input.document_stage_invalid"
    result = invoke_assertions(path, policy_file(tmp_path))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["assertion_batch"]["claims"] == []
    assert payload["assertion_batch"]["entity_mentions"] == []
    assert payload["transformations"][4]["output_ids"] == [payload["assertion_batch"]["batch_id"]]
