"""Minimal dependency-free XLSX BOM adapter for synthetic fixtures."""

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from procurement_intelligence_lab.domains.procurement.assertions import (
    SourceAssertion,
    assertions_for_bom,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domains.procurement.provenance import (
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
_CELL_REFERENCE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


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


def _column_index(reference: str) -> int:
    match = _CELL_REFERENCE.fullmatch(reference.upper())
    if match is None:
        raise ValueError(f"invalid XLSX cell reference: {reference!r}")
    index = 0
    for character in match.group(1):
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _column_name(index: int) -> str:
    name = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _row_values(row: ET.Element, shared_strings: list[str]) -> tuple[list[str], tuple[str, ...]]:
    """Return coordinate-aligned values and the populated source columns."""

    indexed: dict[int, str] = {}
    populated: list[str] = []
    next_index = 0
    for cell in row.findall("x:c", _NS):
        reference = cell.attrib.get("r")
        index = _column_index(reference) if reference else next_index
        indexed[index] = _cell_value(cell, shared_strings)
        populated.append(_column_name(index))
        next_index = index + 1
    width = max(indexed, default=-1) + 1
    return [indexed.get(index, "") for index in range(width)], tuple(populated)


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
        rows: list[tuple[int, list[str], tuple[str, ...]]] = []
        for fallback_row_number, row in enumerate(
            root.findall(".//x:sheetData/x:row", _NS), start=1
        ):
            values, populated_columns = _row_values(row, shared)
            rows.append((int(row.attrib.get("r", fallback_row_number)), values, populated_columns))

    if not rows or rows[0][1][:4] != ["SKU", "Description", "Quantity", "Unit Price"]:
        raise ValueError("expected BOM headers: SKU, Description, Quantity, Unit Price")

    artifact_id = str(path)
    digest = sha256(raw).hexdigest()
    lines: list[BomLine] = []
    for row_number, row, populated_columns in rows[1:]:
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
                EvidenceRef(artifact_id, digest, sheet, row_number, populated_columns),
            )
        )

    artifact_snapshot_id = f"artifact:{digest}"
    context = provenance_context or local_provenance_context()
    context = replace(
        context,
        input_snapshot_ids=tuple(
            dict.fromkeys((*context.input_snapshot_ids, artifact_snapshot_id))
        ),
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
