"""Minimal dependency-free XLSX BOM adapter for synthetic fixtures."""

from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from ..domain.bom import Bom, BomLine, EvidenceRef


_NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _text(node: ET.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def read_bom(path: str | Path, sheet: str = "BOM") -> Bom:
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
        target = next(
            item.attrib["r:id"]
            for item in workbook.findall(".//x:sheet", _NS)
            if item.attrib["name"] == sheet
        )
        worksheet = "xl/" + relmap[target].lstrip("/")
        root = ET.fromstring(archive.read(worksheet))
        rows: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", _NS):
            values: list[str] = []
            for cell in row.findall("x:c", _NS):
                value = _text(cell.find("x:v", _NS))
                if cell.attrib.get("t") == "s":
                    value = shared[int(value)]
                values.append(value)
            rows.append(values)

    if not rows or rows[0][:4] != ["SKU", "Description", "Quantity", "Unit Price"]:
        raise ValueError("expected BOM headers: SKU, Description, Quantity, Unit Price")

    digest = sha256(raw).hexdigest()
    lines = []
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
                EvidenceRef(path.__str__(), digest, sheet, row_number, ("A", "B", "C", "D")),
            )
        )
    return Bom(path.__str__(), tuple(lines))
