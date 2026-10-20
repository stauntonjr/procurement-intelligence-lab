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
    text_value,
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
                for string in strings:
                    _validate_string(string)
                shared = [text_value(string) for string in strings]
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
                    rows[number] = read_row_values(row, shared)
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


def _validate_string(node: ET.Element) -> None:
    texts = node.findall("x:t", NS)
    runs = node.findall("x:r", NS)
    if len(texts) > 1 or (texts and runs) or any(len(run.findall("x:t", NS)) != 1 for run in runs):
        raise DocumentStructureError("string cells require one text value or explicit rich runs")


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
            _validate_string(string)
    elif strings:
        raise DocumentStructureError("scalar/shared cells cannot contain inline strings")
