"""Shared XLSX cell mechanics; no schema mapping or procurement imports."""

import re
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit
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
    rels = (
        _relationships(archive, "xl/_rels/workbook.xml.rels")
        if strict
        else ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    )
    if strict:
        if "_rels/.rels" in archive.namelist():
            entry = _relationship_part(
                _relationships(archive, "_rels/.rels"), "officeDocument", "/"
            )
            if entry != "xl/workbook.xml":
                raise ValueError(
                    "fixed workbook profile requires internal xl/workbook.xml entrypoint"
                )
        if workbook.tag != f"{{{NS['x']}}}workbook" or len(workbook.findall("x:sheets", NS)) != 1:
            raise ValueError("workbook and relationship parts have unsupported structure")
        sheets = workbook.findall("x:sheets/x:sheet", NS)
        for attribute in ("name", "sheetId", f"{{{NS['r']}}}id"):
            values = [node.attrib[attribute] for node in sheets]
            if any(not value for value in values) or len(values) != len(set(values)):
                raise ValueError("worksheet names and identifiers must be nonempty and unique")
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheet_node = next(
        (
            item
            for item in workbook.findall("x:sheets/x:sheet" if strict else ".//x:sheet", NS)
            if item.attrib["name"] == sheet
        ),
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
    if strict and any(
        rel.attrib["Id"] == target and rel.attrib.get("Type") != f"{NS['r']}/worksheet"
        for rel in rels
    ):
        raise ValueError("selected relationship must explicitly identify a worksheet")
    part = _worksheet_part(relmap[target]) if strict else "xl/" + relmap[target].lstrip("/")
    result = ET.fromstring(archive.read(part))
    if strict and (
        result.tag != f"{{{NS['x']}}}worksheet" or len(result.findall("x:sheetData", NS)) != 1
    ):
        raise ValueError("worksheet part requires one direct sheetData element")
    return result


def _worksheet_part(target: str, base: str = "/xl/workbook.xml") -> str:
    if any(
        character.isspace() or ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F
        for character in target
    ):
        raise ValueError("worksheet target cannot contain literal whitespace or control characters")
    uri = urlsplit(target)
    if (
        uri.scheme
        or uri.netloc
        or "?" in target
        or "#" in target
        or not uri.path
        or "//" in target
        or "\\" in target
        or "\x00" in target
    ):
        raise ValueError("worksheet target must be an internal package part URI")
    depth = (
        0 if uri.path.startswith("/") else len([s for s in base.rsplit("/", 1)[0].split("/") if s])
    )
    for segment in uri.path.split("/"):
        if segment == "..":
            if depth == 0:
                raise ValueError("worksheet target escapes the package root")
            depth -= 1
        elif segment not in {"", "."}:
            depth += 1
    part = urljoin(base, target).lstrip("/")
    if not part or part.endswith("/"):
        raise ValueError("worksheet target must identify a part, not a directory")
    return part


def _relationships(archive: ZipFile, path: str) -> ET.Element:
    root = ET.fromstring(archive.read(path))
    namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
    if root.tag != f"{{{namespace}}}Relationships" or any(
        rel.tag != f"{{{namespace}}}Relationship" for rel in root
    ):
        raise ValueError("unsupported relationship part structure")
    identifiers = [rel.attrib["Id"] for rel in root]
    if any(not value for value in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("relationship identifiers must be nonempty and unique")
    return root


def _relationship_part(rels: ET.Element, kind: str, base: str) -> str | None:
    selected = [rel for rel in rels if rel.attrib.get("Type") == f"{NS['r']}/{kind}"]
    if not selected:
        return None
    if len(selected) != 1 or selected[0].attrib.get("TargetMode", "Internal") != "Internal":
        raise ValueError("related part must have one internal relationship")
    return _worksheet_part(selected[0].attrib["Target"], base)


def shared_string_root(archive: ZipFile) -> ET.Element | None:
    """Resolve shared text through workbook metadata, never an orphan filename."""
    part = _relationship_part(
        _relationships(archive, "xl/_rels/workbook.xml.rels"), "sharedStrings", "/xl/workbook.xml"
    )
    if part is None:
        if "xl/sharedStrings.xml" in archive.namelist():
            raise ValueError("shared-string table requires an explicit relationship")
        return None
    result = ET.fromstring(archive.read(part))
    if result.tag != f"{{{NS['x']}}}sst":
        raise ValueError("shared-string part must be an sst table")
    return result
