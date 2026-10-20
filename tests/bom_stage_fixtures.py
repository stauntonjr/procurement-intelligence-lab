"""Synthetic workbook and explicit execution inputs for shared-stage contracts."""

from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

AT = datetime(2026, 10, 19, tzinfo=UTC)
SCOPE = StateScope("synthetic", "bom-stage-contract", "lab", "1")


def provenance() -> DecisionProvenance:
    return DecisionProvenance(
        ProvenanceContext(
            "contract",
            "bom-stages",
            "1",
            "test-revision",
            "uncontainerized",
            "fixture-config",
            None,
            (),
            AT,
        ),
        "test-stage",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def workbook(path: Path, rows: str, *, extra: str = "") -> Path:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + rows
            + "</sheetData>"
            + extra
            + "</worksheet>",
        )
    return path


HEADER = '<row r="1"><c r="A1"><v>SKU</v></c><c r="B1"><v>Description</v></c><c r="C1"><v>Quantity</v></c><c r="D1"><v>Unit Price</v></c></row>'
ROW = (
    '<row r="7"><c r="D7"><v>100.50</v></c><c r="A7"><v>GPU-A</v></c><c r="C7"><v>0.5</v></c></row>'
)


def with_shared_strings(path: Path, content: str) -> None:
    with ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    members["xl/sharedStrings.xml"] = content.encode()
    part = "xl/_rels/workbook.xml.rels"
    relationship = b'<Relationship Id="strings1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    members[part] = members[part].replace(b"</Relationships>", relationship + b"</Relationships>")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
