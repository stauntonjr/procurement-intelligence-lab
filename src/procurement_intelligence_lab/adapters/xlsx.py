"""Minimal dependency-free XLSX BOM adapter for synthetic fixtures."""

from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from procurement_intelligence_lab.adapters.xlsx_cells import (
    NS,
    read_row_values,
    text_value,
    worksheet_root,
)
from procurement_intelligence_lab.domains.procurement.assertions import (
    SourceAssertion,
    assertions_for_bom,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine
from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, TabularLocation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)


_STRUCTURER_NAME = "xlsx-bom-structurer"
_STRUCTURER_VERSION = "1"
_BOM_SCHEMA_VERSION = BOM_TABLE_SCHEMA.schema_id


@dataclass(frozen=True)
class XlsxStructuredBom:
    """A parsed BOM and the event that structured its source artifact."""

    bom: Bom
    transformation: TransformationEvent

    def source_assertions(self) -> tuple[SourceAssertion, ...]:
        """Return assertions that retain both source and execution provenance."""

        return assertions_for_bom(self.bom, self.transformation.event_id)


@dataclass(frozen=True)
class XlsxSourceRow:
    """Original cell text for one admitted worksheet row."""

    sheet: str
    row: int
    headers: tuple[str, ...]
    cells: tuple[str, ...]
    highlighted_columns: tuple[str, ...]


def read_source_row(
    path: str | Path,
    *,
    evidence: EvidenceRef,
) -> XlsxSourceRow:
    """Read the original cells identified by an admitted tabular evidence reference."""

    if not isinstance(evidence.location, TabularLocation):
        raise TypeError("XLSX source viewing requires a tabular evidence location")
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != evidence.content_hash:
        raise ValueError("XLSX source content hash does not match the evidence reference")

    with ZipFile(path) as archive:
        shared = (
            [
                text_value(node)
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(
                    ".//x:si", NS
                )
            ]
            if "xl/sharedStrings.xml" in archive.namelist()
            else []
        )
        root = worksheet_root(archive, evidence.sheet)
        rows = {
            int(row.attrib["r"]): read_row_values(row, shared)
            for row in root.findall(".//x:sheetData/x:row", NS)
            if row.attrib.get("r", "").isdigit()
        }
    if evidence.row not in rows:
        raise ValueError("XLSX source row is not available")
    header_values, _ = rows.get(1, ([], ()))
    row_values, _ = rows[evidence.row]
    width = max(len(header_values), len(row_values))
    headers = tuple(
        header_values[index] if index < len(header_values) else "" for index in range(width)
    )
    cells = tuple(row_values[index] if index < len(row_values) else "" for index in range(width))
    return XlsxSourceRow(
        evidence.sheet,
        evidence.row,
        headers,
        cells,
        evidence.cells,
    )


def read_bom(
    path: str | Path,
    sheet: str = BOM_TABLE_SCHEMA.sheet_name,
    *,
    artifact_id: str | None = None,
) -> Bom:
    """Read a BOM while preserving the original simple adapter boundary."""

    return read_bom_with_provenance(path, sheet, artifact_id=artifact_id).bom


def read_bom_with_provenance(
    path: str | Path,
    sheet: str = BOM_TABLE_SCHEMA.sheet_name,
    provenance_context: ProvenanceContext | None = None,
    implementation_version: str = _STRUCTURER_VERSION,
    schema_version: str = _BOM_SCHEMA_VERSION,
    *,
    artifact_id: str | None = None,
) -> XlsxStructuredBom:
    """Read a BOM and record the deterministic structuring transformation."""

    raw = Path(path).read_bytes()
    with ZipFile(path) as archive:
        shared = (
            [
                text_value(node)
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(
                    ".//x:si", NS
                )
            ]
            if "xl/sharedStrings.xml" in archive.namelist()
            else []
        )
        root = worksheet_root(archive, sheet)
        rows: list[tuple[int, list[str], tuple[str, ...]]] = []
        for fallback_row_number, row in enumerate(
            root.findall(".//x:sheetData/x:row", NS), start=1
        ):
            values, populated_columns = read_row_values(row, shared)
            rows.append((int(row.attrib.get("r", fallback_row_number)), values, populated_columns))

    if not rows or not BOM_TABLE_SCHEMA.matches_headers(rows[0][1]):
        raise ValueError("expected BOM headers: SKU, Description, Quantity, Unit Price")

    artifact_id = artifact_id or str(path)
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
                EvidenceRef(
                    artifact_id,
                    digest,
                    TabularLocation(sheet, row_number, populated_columns),
                ),
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
