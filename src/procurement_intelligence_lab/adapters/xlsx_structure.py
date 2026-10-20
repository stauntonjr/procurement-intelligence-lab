"""Generic XLSX structure recovery from verified captured content, without BOM meaning."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import cast
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError

from procurement_intelligence_lab.adapters.local_artifacts import XLSX_MEDIA_TYPE
from procurement_intelligence_lab.adapters.xlsx_cells import (
    CELL_REFERENCE,
    NS,
    column_index,
    read_row_values,
    worksheet_root,
)
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact
from procurement_intelligence_lab.platform.semantics.documents import (
    StructuredDocument,
    StructuredElement,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArtifactContentError,
    DocumentStructureError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, TabularLocation
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore


@dataclass(frozen=True)
class XlsxStructure:
    store: ArtifactContentStore
    sheet: str

    def structure(
        self, artifact: Artifact, *, provenance: DecisionProvenance
    ) -> StructuredDocument:
        content = self.store.get(artifact.content_hash)
        if not isinstance(cast(object, content), bytes):
            raise ArtifactContentError("captured content must be immutable bytes")
        if (
            len(content) != artifact.byte_length
            or sha256(content).hexdigest() != artifact.content_hash
        ):
            raise ArtifactContentError("captured bytes do not match artifact hash and length")
        if artifact.media_type != XLSX_MEDIA_TYPE:
            raise DocumentStructureError("XLSX structuring requires the XLSX media type")
        try:
            with ZipFile(BytesIO(content)) as archive:
                if len(archive.namelist()) != len(set(archive.namelist())):
                    raise DocumentStructureError("duplicate XLSX archive members are unsupported")
                strings = (
                    ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("x:si", NS)
                    if "xl/sharedStrings.xml" in archive.namelist()
                    else []
                )
                shared = [_string_value(string) for string in strings]
                root = worksheet_root(archive, self.sheet, strict=True)
                if root.find("x:mergeCells", NS) is not None:
                    raise DocumentStructureError("merged-cell worksheets are unsupported")
                rows: dict[int, tuple[list[str], tuple[str, ...]]] = {}
                for fallback, row in enumerate(root.findall(".//x:sheetData/x:row", NS), start=1):
                    number = int(row.attrib.get("r", fallback))
                    if number < 1 or number > 1_048_576 or number in rows:
                        raise DocumentStructureError(
                            "worksheet row coordinates must be within the XLSX grid and unique"
                        )
                    indices: set[int] = set()
                    next_index = 0
                    for cell in row.findall("x:c", NS):
                        _validate_cell(cell)
                        reference = cell.attrib.get("r")
                        if reference:
                            match = CELL_REFERENCE.fullmatch(reference.upper())
                            if match is None or int(match.group(2)) != number:
                                raise DocumentStructureError("cell and row coordinates conflict")
                        index = column_index(reference) if reference else next_index
                        if index > 16_383:
                            raise DocumentStructureError("cell column exceeds the XLSX grid")
                        if cell.attrib.get("t") == "s" and not (
                            0 <= int(cell.findtext("x:v", "", NS)) < len(shared)
                        ):
                            raise DocumentStructureError(
                                "shared-string index is outside the captured table"
                            )
                        if index in indices:
                            raise DocumentStructureError(
                                "worksheet cell coordinates must be unique"
                            )
                        if cell.find("x:f", NS) is not None:
                            raise DocumentStructureError(
                                "formula cells are unsupported; cached values are not recalculated"
                            )
                        indices.add(index)
                        next_index = index + 1
                    rows[number] = read_row_values(row, shared, inline_decoder=_string_value)
        except (
            BadZipFile,
            KeyError,
            IndexError,
            ValueError,
            ET.ParseError,
            OverflowError,
            RuntimeError,
            NotImplementedError,
            EOFError,
            ZlibError,
        ) as exc:
            if isinstance(exc, DocumentStructureError):
                raise
            raise DocumentStructureError(
                "captured bytes are not a supported XLSX worksheet"
            ) from None
        elements: list[StructuredElement] = []
        for number, (values, columns) in sorted(rows.items()):
            if not columns:
                continue
            ordered = tuple(sorted(columns, key=lambda column: column_index(column + "1")))
            row_evidence = EvidenceRef(
                artifact.artifact_id,
                artifact.content_hash,
                TabularLocation(self.sheet, number, ordered),
            )
            elements.append(
                StructuredElement(
                    stable_id("xlsx-row", row_evidence.evidence_id),
                    "row",
                    len(elements),
                    "",
                    row_evidence,
                )
            )
            for column in ordered:
                evidence = EvidenceRef(
                    artifact.artifact_id,
                    artifact.content_hash,
                    TabularLocation(self.sheet, number, (column,)),
                )
                elements.append(
                    StructuredElement(
                        stable_id("xlsx-cell", evidence.evidence_id),
                        "cell",
                        len(elements),
                        values[column_index(column + "1")],
                        evidence,
                    )
                )
        return StructuredDocument(artifact, tuple(elements), provenance)


def _string_value(node: ET.Element | None) -> str:
    if node is None:
        return ""
    texts = node.findall("x:t", NS)
    runs = node.findall("x:r", NS)

    def tag(name: str) -> str:
        return f"{{{NS['x']}}}{name}"

    if (
        (node.text or "").strip()
        or len(texts) > 1
        or (texts and runs)
        or any(child.tag not in {tag("t"), tag("r")} for child in node)
        or any((child.tail or "").strip() for child in node)
    ):
        raise DocumentStructureError("unsupported or conflicting string content")
    leaves = list(texts)
    properties = {
        tag(name)
        for name in (
            "rFont",
            "charset",
            "family",
            "b",
            "i",
            "strike",
            "outline",
            "shadow",
            "condense",
            "extend",
            "color",
            "sz",
            "u",
            "vertAlign",
            "scheme",
        )
    }
    for run in runs:
        display = run.findall("x:t", NS)
        styles = run.findall("x:rPr", NS)
        if (
            len(display) != 1
            or len(styles) > 1
            or (run.text or "").strip()
            or any(child.tag not in {tag("t"), tag("rPr")} for child in run)
            or any((child.tail or "").strip() for child in run)
        ):
            raise DocumentStructureError("malformed rich-string run")
        for style in styles:
            if (
                (style.text or "").strip()
                or len({child.tag for child in style}) != len(style)
                or any(
                    child.tag not in properties
                    or len(child)
                    or (child.text or "").strip()
                    or (child.tail or "").strip()
                    for child in style
                )
            ):
                raise DocumentStructureError("unsupported rich-string properties")
        leaves.extend(display)
    if any(len(leaf) for leaf in leaves):
        raise DocumentStructureError("string text must be a leaf value")
    return "".join(leaf.text or "" for leaf in leaves)


def _validate_cell(cell: ET.Element) -> None:
    kind = cell.attrib.get("t", "n")
    if kind not in {"n", "s", "inlineStr", "str", "b", "d"}:
        raise DocumentStructureError("unsupported XLSX cell type")
    values = cell.findall("x:v", NS)
    strings = cell.findall("x:is", NS)
    if len(values) > 1 or len(strings) > 1 or any(len(value) for value in values):
        raise DocumentStructureError("cell content must have a single scalar or inline value")
    if kind == "inlineStr":
        if values:
            raise DocumentStructureError("inline string cells cannot contain scalar values")
        for string in strings:
            _string_value(string)
    elif strings:
        raise DocumentStructureError("scalar/shared cells cannot contain inline strings")
