from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, workbook

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / "tests/fixtures/bom-stages/context.json"
pytestmark = pytest.mark.integration


def invoke(source: Path, context: Path = CONTEXT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.bom_stages",
            str(source),
            "--context",
            str(context),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=source.parent,
    )


def test_cli_executes_first_three_stages_with_source_and_transformation_links(
    tmp_path: Path,
) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    result = invoke(path)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    data = json.loads(result.stdout)
    assert data["executed_stages"] == ["INGEST", "STRUCTURE", "MAP"]
    assert data["artifact"]["source"]["scope"]["tenant_id"] == "synthetic"
    assert data["artifact"]["source"]["source_uri"] == path.as_uri()
    fields = {f["field_name"]: f for f in data["mapped_document"]["fields"]}
    assert fields["quantity"]["raw_value"] == "0.5"
    assert fields["quantity"]["evidence"]["cells"] == ["C"]
    assert fields["quantity"]["evidence"]["artifact_id"] == data["artifact"]["artifact_id"]
    assert fields["description"]["raw_value"] is None
    assert fields["description"]["status"] == "unresolved"
    events = data["transformations"]
    assert len(events) == 3 and len({e["event_id"] for e in events}) == 3
    assert events[0]["output_ids"] == [data["artifact"]["artifact_id"]]
    assert events[1]["parent_event_ids"] == [events[0]["event_id"]]
    assert events[2]["parent_event_ids"] == [events[1]["event_id"]]
    assert events[2]["output_ids"] == [data["mapped_document"]["mapped_document_id"]]
    assert invoke(path).stdout == result.stdout


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("bad_source", "pil.interpretation.document_structure_invalid"),
        ("missing_source", "pil.infrastructure.artifact_source_unavailable"),
        ("bad_header", "pil.interpretation.schema_mapping_invalid"),
        ("context_missing", "pil.input.document_stage_invalid"),
        ("context_unknown", "pil.input.document_stage_invalid"),
        ("context_duplicate", "pil.input.document_stage_invalid"),
        ("context_numeric", "pil.input.document_stage_invalid"),
        ("context_naive", "pil.input.document_stage_invalid"),
        ("context_future", "pil.input.temporal_contract_violation"),
    ],
)
def test_cli_failures_are_typed_without_partial_success(
    tmp_path: Path, change: str, code: str
) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    context = tmp_path / "context.json"
    data = json.loads(CONTEXT.read_text())
    if change == "bad_source":
        path.write_bytes(b"not xlsx")
    elif change == "missing_source":
        path.unlink()
    elif change == "bad_header":
        workbook(path, HEADER.replace("SKU", "Other") + ROW)
    elif change == "context_unknown":
        data["unknown"] = True
    elif change == "context_numeric":
        data["run_id"] = 0
    elif change == "context_naive":
        data["observed_at"] = "2026-10-19T00:00:00"
    elif change == "context_future":
        data["observed_at"] = "2026-10-20T00:00:00+00:00"
    if change == "context_duplicate":
        context.write_text('{"run_id":"a","run_id":"b"}')
    elif change != "context_missing":
        context.write_text(json.dumps(data))
    result = invoke(path, context)
    assert result.returncode == 2
    assert not result.stdout
    assert json.loads(result.stderr)["code"] == code
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_sheet_name",
        "duplicate_sheet_id",
        "duplicate_relationship",
        "external_relationship",
        "unknown_cell_type",
        "duplicate_value",
        "duplicate_inline",
        "mixed_value_inline",
        "duplicate_inline_text",
        "duplicate_shared_text",
    ],
)
def test_cli_rejects_ambiguous_workbook_and_cell_representations(
    tmp_path: Path, change: str
) -> None:
    path = workbook(tmp_path / "ambiguous.xlsx", HEADER + ROW)
    with ZipFile(path) as archive:
        members = {name: archive.read(name).decode() for name in archive.namelist()}
    book = "xl/workbook.xml"
    rels = "xl/_rels/workbook.xml.rels"
    sheet = "xl/worksheets/sheet1.xml"
    if change == "duplicate_sheet_name":
        members[book] = members[book].replace(
            "</sheets>", '<sheet name="BOM" sheetId="2" r:id="rId2"/></sheets>'
        )
    elif change == "duplicate_sheet_id":
        members[book] = members[book].replace(
            "</sheets>", '<sheet name="Other" sheetId="1" r:id="rId2"/></sheets>'
        )
    elif change == "duplicate_relationship":
        members[rels] = members[rels].replace(
            "</Relationships>",
            '<Relationship Id="rId1" Target="worksheets/sheet2.xml"/></Relationships>',
        )
        members["xl/worksheets/sheet2.xml"] = members[sheet].replace("0.5", "9000")
    elif change == "external_relationship":
        members[rels] = members[rels].replace('Id="rId1"', 'Id="rId1" TargetMode="External"')
    elif change == "duplicate_shared_text":
        members[sheet] = members[sheet].replace(
            '<c r="C7"><v>0.5</v></c>', '<c r="C7" t="s"><v>0</v></c>'
        )
        members["xl/sharedStrings.xml"] = (
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>0.5</t><t>9000</t></si></sst>"
        )
    else:
        replacement = {
            "unknown_cell_type": '<c r="C7" t="unsupported"><v>0.5</v></c>',
            "duplicate_value": '<c r="C7"><v>0.5</v><v>9000</v></c>',
            "duplicate_inline": '<c r="C7" t="inlineStr"><is><t>0.5</t></is><is><t>9000</t></is></c>',
            "mixed_value_inline": '<c r="C7" t="inlineStr"><v>9000</v><is><t>0.5</t></is></c>',
            "duplicate_inline_text": '<c r="C7" t="inlineStr"><is><t>0.5</t><t>9000</t></is></c>',
        }[change]
        members[sheet] = members[sheet].replace('<c r="C7"><v>0.5</v></c>', replacement)
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    result = invoke(path)
    assert result.returncode == 2, result.stdout
    assert not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.interpretation.document_structure_invalid"
