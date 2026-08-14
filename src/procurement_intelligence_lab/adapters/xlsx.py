"""Minimal dependency-free XLSX BOM adapter for synthetic fixtures."""

from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from procurement_intelligence_lab.domain.assertions import (
    SourceAssertion,
    assertions_for_bom,
)
from procurement_intelligence_lab.domain.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
    local_provenance_context,
)


_NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
_STRUCTURER_NAME = "xlsx-bom-structurer"
_STRUCTURER_VERSION = "1"
_BOM_SCHEMA_VERSION = "bom-xlsx-v1"


@dataclass(frozen=True)
class XlsxStructuredBom:
    """A parsed BOM and the event that structured its source artifact."""

    bom: Bom
    transformation: TransformationEvent

    def source_assertions(self) -> tuple[SourceAssertion, ...]:
        """Return assertions that retain both source and execution provenance."""

        return assertions_for_bom(self.bom, self.transformation.event_id)


def _text(node: ET.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return _text(cell.find("x:is", _NS))
    value = _text(cell.find("x:v", _NS))
    return shared_strings[int(value)] if cell.attrib.get("t") == "s" else value


def read_bom(path: str | Path, sheet: str = "BOM") -> Bom:
    """Read a BOM while preserving the original simple adapter boundary."""

    return read_bom_with_provenance(path, sheet).bom


def read_bom_with_provenance(
    path: str | Path,
    sheet: str = "BOM",
    provenance_context: ProvenanceContext | None = None,
    implementation_version: str = _STRUCTURER_VERSION,
    schema_version: str = _BOM_SCHEMA_VERSION,
) -> XlsxStructuredBom:
    """Read a BOM and record the deterministic structuring transformation."""

    raw = Path(path).read_bytes()
    with ZipFile(path) as archive:
        shared = (
            [
                _text(node)
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(
                    ".//x:si", _NS
                )
            ]
            if "xl/sharedStrings.xml" in archive.namelist()
            else []
        )
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheet_node = next(
            (item for item in workbook.findall(".//x:sheet", _NS) if item.attrib["name"] == sheet),
            None,
        )
        if sheet_node is None:
            raise ValueError(f"sheet {sheet!r} not found in workbook")
        target = sheet_node.attrib.get(f"{{{_NS['r']}}}id", sheet_node.attrib.get("r:id", ""))
        if not target or target not in relmap:
            raise ValueError(f"sheet {sheet!r} has no valid relationship")
        worksheet = "xl/" + relmap[target].lstrip("/")
        root = ET.fromstring(archive.read(worksheet))
        rows: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", _NS):
            rows.append([_cell_value(cell, shared) for cell in row.findall("x:c", _NS)])

    if not rows or rows[0][:4] != ["SKU", "Description", "Quantity", "Unit Price"]:
        raise ValueError("expected BOM headers: SKU, Description, Quantity, Unit Price")

    artifact_id = str(path)
    digest = sha256(raw).hexdigest()
    lines: list[BomLine] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or not row[0]:
            continue
        padded = row + [""] * (4 - len(row))
        price = Decimal(padded[3]) if padded[3] else None
        lines.append(
            BomLine(
                padded[0],
                padded[1],
                Decimal(padded[2]),
                price,
                EvidenceRef(artifact_id, digest, sheet, row_number, ("A", "B", "C", "D")),
            )
        )

    artifact_snapshot_id = f"artifact:{digest}"
    context = provenance_context or local_provenance_context()
    context = replace(
        context,
        input_snapshot_ids=tuple(\n            dict.fromkeys((*context.input_snapshot_ids, artifact_snapshot_id))\n        ),
    )
    provenance = DecisionProvenance(
        context,
        _STRUCTURER_NAME,
        ComponentKind.DETERMINISTIC,
        implementation_version,
        schema_version=schema_version,
    )
    bom = Bom(artifact_id, tuple(lines))
    transformation = TransformationEvent(
        "document-structuring",
        provenance,
        (
            ProvenanceEdge(ProvenanceRelation.USED_INPUT, artifact_snapshot_id),
            ProvenanceEdge(ProvenanceRelation.USED_SCHEMA, f"schema:{schema_version}"),
        ),
        (f"structured-bom:{digest}:{sheet}",),
    )
    return XlsxStructuredBom(bom, transformation)
