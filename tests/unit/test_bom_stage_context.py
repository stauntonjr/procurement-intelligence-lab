from __future__ import annotations

import json
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces.bom_stages import main
from tests.bom_stage_fixtures import HEADER, ROW, workbook

CONTEXT = Path(__file__).resolve().parents[1] / "fixtures/bom-stages/context.json"


@pytest.mark.parametrize(
    "case",
    [
        "scalar",
        "missing",
        "scope_list",
        "scope_extra",
        "scope_empty",
        "unicode",
        "bad_time",
        "bad_version",
        "nonfinite",
        "valid",
    ],
)
def test_in_process_public_entry_validates_context_types_and_serializes_actual_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], case: str
) -> None:
    data = json.loads(CONTEXT.read_text())
    source = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    if case == "scalar":
        data = []
    elif case == "missing":
        data.pop("run_id")
    elif case == "scope_list":
        data["scope"] = []
    elif case == "scope_extra":
        data["scope"]["extra"] = True
    elif case == "scope_empty":
        data["scope"]["project_id"] = " "
    elif case == "unicode":
        data["code_revision"] = "\ud800"
    elif case == "bad_time":
        data["captured_at"] = "not-a-date"
    elif case == "bad_version":
        data["source_version"] = {}
    elif case == "nonfinite":
        data["run_id"] = float("nan")
    context = tmp_path / "context.json"
    context.write_text(json.dumps(data))
    monkeypatch.setattr("sys.argv", ["bom_stages", str(source), "--context", str(context)])
    code = main()
    out = capsys.readouterr()
    if case == "valid":
        assert code == 0 and not out.err
        result = json.loads(out.out)
        assert result["transformations"][2]["provenance"]["schema_version"] == "bom-xlsx-v1"
        assert (
            result["structured_document"]["provenance"]["component_name"] == "xlsx-cell-structure"
        )
        assert len(result["mapped_document"]["fields"]) == 4
    else:
        assert code == 2 and not out.out
        assert json.loads(out.err)["code"] == "pil.input.document_stage_invalid"
