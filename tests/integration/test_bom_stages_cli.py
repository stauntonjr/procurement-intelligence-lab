from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests.bom_stage_fixtures import HEADER, ROW, with_shared_strings, workbook

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
        "phonetic_annotation",
        "nested_text",
        "rich_property_text",
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
        members["xl/_rels/workbook.xml.rels"] = members["xl/_rels/workbook.xml.rels"].replace(
            "</Relationships>",
            '<Relationship Id="strings1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
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
            "phonetic_annotation": '<c r="C7" t="inlineStr"><is><t>0.5</t><rPh sb="0" eb="3"><t>9000</t></rPh></is></c>',
            "nested_text": '<c r="C7" t="inlineStr"><is><t>0.5<t>9000</t></t></is></c>',
            "rich_property_text": '<c r="C7" t="inlineStr"><is><r><rPr><t>9000</t></rPr><t>0.5</t></r></is></c>',
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


@pytest.mark.parametrize("kind", ["inlineStr", "s"])
def test_cli_recovers_only_rich_display_text_without_xml_indentation(
    tmp_path: Path, kind: str
) -> None:
    rich = "<r><rPr><b/></rPr><t>0.</t></r>\n  <r><t>5</t></r>"
    value = f'<c r="C7" t="inlineStr"><is>\n  {rich}\n</is></c>'
    if kind == "s":
        value = '<c r="C7" t="s"><v>0</v></c>'
    path = workbook(tmp_path / "rich.xlsx", HEADER + ROW.replace('<c r="C7"><v>0.5</v></c>', value))
    if kind == "s":
        with_shared_strings(
            path,
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<si>\n  {rich}\n</si></sst>",
        )
    result = invoke(path)
    assert result.returncode == 0, result.stderr
    fields = json.loads(result.stdout)["mapped_document"]["fields"]
    assert next(f for f in fields if f["field_name"] == "quantity")["raw_value"] == "0.5"


@pytest.mark.parametrize(
    ("target", "accepted"),
    [
        ("/xl/worksheets/sheet1.xml", True),
        ("worksheets/../worksheets/sheet1.xml", True),
        ("../xl/worksheets/sheet1.xml", True),
        ("../../xl/worksheets/sheet1.xml", False),
        ("worksheets/sheet1.x&#10;ml", False),
        ("worksheets/sheet1.x&#9;ml", False),
        (" worksheets/sheet1.xml", False),
        ("worksheets//sheet1.xml", False),
        ("///xl/worksheets/sheet1.xml", False),
        ("worksheets/sheet1.xml?", False),
        ("worksheets/sheet1.xml#", False),
        (".", False),
        ("/", False),
        ("//example.invalid/sheet.xml", False),
        ("https://example.invalid/sheet.xml", False),
        ("worksheets/sheet1.xml?query=1", False),
        ("worksheets/sheet1.xml#fragment", False),
    ],
)
def test_cli_resolves_internal_worksheet_target_uris(
    tmp_path: Path, target: str, accepted: bool
) -> None:
    path = workbook(tmp_path / "uri.xlsx", HEADER + ROW)
    with ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    rels = "xl/_rels/workbook.xml.rels"
    members[rels] = members[rels].replace(b"worksheets/sheet1.xml", target.encode())
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    result = invoke(path)
    if not accepted:
        assert result.returncode == 2 and not result.stdout
        assert json.loads(result.stderr)["code"] == "pil.interpretation.document_structure_invalid"
        return
    assert result.returncode == 0, result.stderr
    fields = json.loads(result.stdout)["mapped_document"]["fields"]
    assert next(f for f in fields if f["field_name"] == "quantity")["raw_value"] == "0.5"


@pytest.mark.parametrize(
    "change",
    [
        "missing_type",
        "wrong_type",
        "workbook_root",
        "relationships_root",
        "relationship_element",
        "worksheet_root",
        "nested_sheet_data",
        "duplicate_sheet_data",
        "shared_root",
        "nested_sheets",
    ],
)
def test_cli_requires_worksheet_relationship_and_physical_part_shape(
    tmp_path: Path, change: str
) -> None:
    path = workbook(tmp_path / "part.xlsx", HEADER + ROW)
    with ZipFile(path) as archive:
        members = {name: archive.read(name).decode() for name in archive.namelist()}
    book, rels, sheet = "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml"
    worksheet_type = (
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
    )
    if change == "missing_type":
        members[rels] = members[rels].replace(worksheet_type, "")
    elif change == "wrong_type":
        members[rels] = members[rels].replace("relationships/worksheet", "relationships/styles")
    elif change == "workbook_root":
        members[book] = (
            members[book].replace("<workbook ", "<other ").replace("</workbook>", "</other>")
        )
    elif change == "relationships_root":
        members[rels] = (
            members[rels]
            .replace("<Relationships ", "<Other ")
            .replace("</Relationships>", "</Other>")
        )
    elif change == "relationship_element":
        members[rels] = members[rels].replace("<Relationship ", "<Other ")
    elif change == "worksheet_root":
        members[sheet] = (
            members[sheet]
            .replace("<worksheet ", "<styleSheet ")
            .replace("</worksheet>", "</styleSheet>")
        )
    elif change == "nested_sheet_data":
        members[sheet] = (
            members[sheet]
            .replace("<sheetData>", "<ext><sheetData>")
            .replace("</sheetData>", "</sheetData></ext>")
        )
    elif change == "duplicate_sheet_data":
        members[sheet] = members[sheet].replace(HEADER, HEADER + "</sheetData><sheetData>")
    elif change == "nested_sheets":
        members[book] = (
            members[book]
            .replace("<sheets>", "<ext><sheets>")
            .replace("</sheets>", "</sheets></ext>")
        )
    else:
        members[sheet] = members[sheet].replace(
            '<c r="C7"><v>0.5</v></c>', '<c r="C7" t="s"><v>0</v></c>'
        )
        members["xl/_rels/workbook.xml.rels"] = members["xl/_rels/workbook.xml.rels"].replace(
            "</Relationships>",
            '<Relationship Id="strings1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
        )
        members["xl/sharedStrings.xml"] = (
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>0.5</t></si></styleSheet>'
        )
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    result = invoke(path)
    assert result.returncode == 2, result.stdout
    assert not result.stdout
    assert json.loads(result.stderr)["code"] == "pil.interpretation.document_structure_invalid"


@pytest.mark.parametrize("change", ["redirect", "missing", "duplicate", "external"])
def test_cli_selects_shared_strings_by_relationship_not_orphan_filename(
    tmp_path: Path, change: str
) -> None:
    path = workbook(
        tmp_path / "shared.xlsx",
        HEADER + ROW.replace('<c r="C7"><v>0.5</v></c>', '<c r="C7" t="s"><v>0</v></c>'),
    )
    with ZipFile(path) as archive:
        members = {name: archive.read(name).decode() for name in archive.namelist()}
    table = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>{}</t></si></sst>'
    members["xl/sharedStrings.xml"] = table.format("9000")
    members["xl/strings/actual.xml"] = table.format("0.5")
    relationship = '<Relationship Id="strings1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="strings/actual.xml"/>'
    if change == "external":
        relationship = relationship.replace('Id="strings1"', 'Id="strings1" TargetMode="External"')
    elif change == "duplicate":
        relationship += relationship.replace('Id="strings1"', 'Id="strings2"')
    elif change == "missing":
        relationship = ""
    members["xl/_rels/workbook.xml.rels"] = members["xl/_rels/workbook.xml.rels"].replace(
        "</Relationships>", relationship + "</Relationships>"
    )
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    result = invoke(path)
    if change == "redirect":
        assert result.returncode == 0, result.stderr
        fields = json.loads(result.stdout)["mapped_document"]["fields"]
        assert next(f for f in fields if f["field_name"] == "quantity")["raw_value"] == "0.5"
    else:
        assert result.returncode == 2 and not result.stdout
        assert json.loads(result.stderr)["code"] == "pil.interpretation.document_structure_invalid"


@pytest.mark.parametrize(
    "change", ["matching", "redirect", "missing_type", "duplicate", "external"]
)
def test_cli_fixed_workbook_profile_rejects_contradictory_root_relationships(
    tmp_path: Path, change: str
) -> None:
    path = workbook(tmp_path / "root.xlsx", HEADER + ROW)
    with ZipFile(path) as archive:
        members = {name: archive.read(name).decode() for name in archive.namelist()}
    relationship = '<Relationship Id="root1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    if change == "redirect":
        relationship = relationship.replace("xl/workbook.xml", "other/workbook.xml")
        members["other/workbook.xml"] = members["xl/workbook.xml"]
        members["other/_rels/workbook.xml.rels"] = members["xl/_rels/workbook.xml.rels"]
        members["other/worksheets/sheet1.xml"] = members["xl/worksheets/sheet1.xml"].replace(
            "0.5", "9000"
        )
    elif change == "missing_type":
        relationship = relationship.replace(
            ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"',
            "",
        )
    elif change == "duplicate":
        relationship += relationship.replace('Id="root1"', 'Id="root2"')
    elif change == "external":
        relationship = relationship.replace('Id="root1"', 'Id="root1" TargetMode="External"')
    members["_rels/.rels"] = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + relationship
        + "</Relationships>"
    )
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    result = invoke(path)
    if change == "matching":
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode == 2 and not result.stdout
        assert json.loads(result.stderr)["code"] == "pil.interpretation.document_structure_invalid"
