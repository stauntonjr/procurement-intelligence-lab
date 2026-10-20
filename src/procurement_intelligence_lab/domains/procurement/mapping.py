"""Procurement-owned schema meaning over generic tabular structure, without numeric policy."""

from dataclasses import dataclass

from procurement_intelligence_lab.domains.procurement.source_schema import (
    BOM_TABLE_SCHEMA,
    BomTableSchema,
)
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    MappedField,
    StructuredDocument,
    StructuredElement,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import SchemaMappingError
from procurement_intelligence_lab.platform.semantics.evidence import TabularLocation
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance

_FIELD_NAMES = ("sku", "description", "quantity", "unit_price")
_COLUMNS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class BomTableMap:
    schema: BomTableSchema = BOM_TABLE_SCHEMA

    def map_document(
        self, document: StructuredDocument, *, provenance: DecisionProvenance
    ) -> MappedDocument:
        rows: dict[int, StructuredElement] = {}
        cells: dict[tuple[int, str], StructuredElement] = {}
        for element in document.elements:
            location = element.evidence.location
            if (
                not isinstance(location, TabularLocation)
                or location.sheet != self.schema.sheet_name
            ):
                raise SchemaMappingError("BOM mapping requires the configured tabular worksheet")
            if element.kind == "row":
                if location.row in rows:
                    raise SchemaMappingError("duplicate structured row evidence")
                rows[location.row] = element
            elif element.kind == "cell" and len(location.cells) == 1:
                key = (location.row, location.cells[0])
                if key in cells:
                    raise SchemaMappingError("duplicate structured cell evidence")
                cells[key] = element
            else:
                raise SchemaMappingError("unsupported structured element for BOM mapping")
        if not rows:
            raise SchemaMappingError("BOM headers are missing")
        for number, row in rows.items():
            actual = {column for row_number, column in cells if row_number == number}
            if set(row.evidence.cells) != actual:
                raise SchemaMappingError("structured row and cell evidence disagree")
        if any(number not in rows for number, _ in cells):
            raise SchemaMappingError("structured cell has no source row")
        header = min(rows)
        headers = tuple(
            cells[(header, col)].text if (header, col) in cells else "" for col in _COLUMNS
        )
        if not self.schema.matches_headers(headers):
            raise SchemaMappingError(
                "expected distinct ordered BOM headers: SKU, Description, Quantity, Unit Price"
            )
        fields: list[MappedField] = []
        for number, row in sorted(rows.items()):
            if number == header:
                continue
            for column, name in zip(_COLUMNS, _FIELD_NAMES, strict=True):
                element = cells.get((number, column))
                value = element.text if element is not None and element.text else None
                diagnostic = (
                    None
                    if value is not None
                    else ("blank cell" if element is not None else f"missing column {column}")
                )
                fields.append(
                    MappedField(
                        f"{self.schema.sheet_name}!{column}{number}",
                        name,
                        value,
                        element.evidence if element is not None else row.evidence,
                        EpistemicStatus.OBSERVED
                        if value is not None
                        else EpistemicStatus.UNRESOLVED,
                        diagnostic,
                    )
                )
            for (row_number, column), element in sorted(cells.items()):
                if row_number != number or column in _COLUMNS:
                    continue
                fields.append(
                    MappedField(
                        f"{self.schema.sheet_name}!{column}{number}",
                        f"unmapped.{column}",
                        element.text or None,
                        element.evidence,
                        EpistemicStatus.OBSERVED if element.text else EpistemicStatus.UNRESOLVED,
                        f"unmapped column {column}"
                        if element.text
                        else f"blank unmapped column {column}",
                    )
                )
        return MappedDocument(document, self.schema.reference_id, tuple(fields), provenance)
