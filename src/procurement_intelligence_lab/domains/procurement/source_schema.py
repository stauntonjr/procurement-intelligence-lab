"""Domain-owned source shape for the existing constrained BOM table."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BomTableSchema:
    """Four ordered BOM fields; additional trailing source columns remain permitted."""

    reference_id: str
    schema_id: str
    sheet_name: str
    columns: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.reference_id, self.schema_id, self.sheet_name)):
            raise ValueError("BOM schema requires reference, schema and sheet identities")
        if (
            len(self.columns) != 4
            or len(set(self.columns)) != 4
            or any(not value.strip() for value in self.columns)
        ):
            raise ValueError("BOM schema requires four distinct non-empty column labels")

    def matches_headers(self, headers: Sequence[str]) -> bool:
        return tuple(headers[: len(self.columns)]) == self.columns


BOM_TABLE_SCHEMA = BomTableSchema(
    reference_id="procurement.mapping/bom-table@1",
    schema_id="bom-xlsx-v1",
    sheet_name="BOM",
    columns=("SKU", "Description", "Quantity", "Unit Price"),
)
