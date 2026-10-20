"""Shared XLSX cell mechanics; no schema mapping or procurement imports."""

import re
from collections.abc import Callable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
CELL_REFERENCE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


def text_value(node: ET.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def _cell_value(
    cell: ET.Element,
    shared_strings: list[str],
    inline_decoder: Callable[[ET.Element | None], str],
) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return inline_decoder(cell.find("x:is", NS))
    value = text_value(cell.find("x:v", NS))
    return shared_strings[int(value)] if cell.attrib.get("t") == "s" else value


def column_index(reference: str) -> int:
    match = CELL_REFERENCE.fullmatch(reference.upper())
    if match is None:
        raise ValueError(f"invalid XLSX cell reference: {reference!r}")
    index = 0
    for character in match.group(1):
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def column_name(index: int) -> str:
    name = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def read_row_values(
    row: ET.Element,
    shared_strings: list[str],
    *,
    inline_decoder: Callable[[ET.Element | None], str] = text_value,
) -> tuple[list[str], tuple[str, ...]]:
    """Return coordinate-aligned values and the populated source columns."""

    indexed: dict[int, str] = {}
    populated: list[str] = []
    next_index = 0
    for cell in row.findall("x:c", NS):
        reference = cell.attrib.get("r")
        index = column_index(reference) if reference else next_index
        indexed[index] = _cell_value(cell, shared_strings, inline_decoder)
        populated.append(column_name(index))
        next_index = index + 1
    width = max(indexed, default=-1) + 1
    return [indexed.get(index, "") for index in range(width)], tuple(populated)


def worksheet_root(archive: ZipFile, sheet: str, *, strict: bool = False) -> ET.Element:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    if strict:
        sheets = workbook.findall(".//x:sheet", NS)
        for attribute in ("name", "sheetId", f"{{{NS['r']}}}id"):
            values = [node.attrib[attribute] for node in sheets]
            if any(not value for value in values) or len(values) != len(set(values)):
                raise ValueError("worksheet names and identifiers must be nonempty and unique")
        identifiers = [rel.attrib["Id"] for rel in rels]
        if any(not value for value in identifiers) or len(identifiers) != len(set(identifiers)):
            raise ValueError("worksheet relationship identifiers must be nonempty and unique")
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheet_node = next(
        (item for item in workbook.findall(".//x:sheet", NS) if item.attrib["name"] == sheet),
        None,
    )
    if sheet_node is None:
        raise ValueError(f"sheet {sheet!r} not found in workbook")
    target = sheet_node.attrib.get(f"{{{NS['r']}}}id", sheet_node.attrib.get("r:id", ""))
    if not target or target not in relmap:
        raise ValueError(f"sheet {sheet!r} has no valid relationship")
    if strict and any(
        rel.attrib["Id"] == target and rel.attrib.get("TargetMode", "Internal") != "Internal"
        for rel in rels
    ):
        raise ValueError("external worksheet relationships are unsupported")
    return ET.fromstring(archive.read("xl/" + relmap[target].lstrip("/")))
