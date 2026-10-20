"""Explicit, evidence-preserving normalization for the constrained BOM table."""

import re
from dataclasses import dataclass
from decimal import Context, Decimal
from enum import StrEnum

from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA
from procurement_intelligence_lab.platform.semantics.documents import MappedDocument, MappedField
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    NormalizationError,
    NormalizationPolicyError,
)
from procurement_intelligence_lab.platform.semantics.evidence import TabularLocation
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance

_COLUMNS = {"A": "sku", "B": "description", "C": "quantity", "D": "unit_price"}


class CountUnit(StrEnum):
    EACH = "each"
    DOZEN = "dozen"


@dataclass(frozen=True)
class BomNormalizationPolicy:
    quantity_unit: CountUnit
    currency: str
    price_unit: CountUnit

    def __post_init__(self) -> None:
        if type(self.quantity_unit) is not CountUnit or type(self.price_unit) is not CountUnit:
            raise NormalizationPolicyError("quantity and price units must be explicit each/dozen")
        if type(self.currency) is not str or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise NormalizationPolicyError(
                "currency must be an explicit three-uppercase-letter label"
            )

    @property
    def reference_id(self) -> str:
        return stable_id(
            "bom-normalization-policy",
            "1",
            self.quantity_unit.value,
            self.currency,
            self.price_unit.value,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "profile": "bom-decimal@1",
            "quantity_unit": self.quantity_unit.value,
            "currency": self.currency,
            "price_unit": self.price_unit.value,
            "reference_id": self.reference_id,
        }


def _decimal(field: MappedField) -> Decimal:
    raw = field.raw_value
    if not isinstance(raw, str):
        raise NormalizationError(f"{field.field_key}: numeric source must be text")
    text = raw.strip(" \t\r\n")
    if len(text) > 128 or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", text) is None:
        raise NormalizationError(
            f"{field.field_key}: expected ASCII fixed-point decimal, at most 128 characters"
        )
    return Decimal(text)


@dataclass(frozen=True)
class BomNormalize:
    policy: BomNormalizationPolicy

    def __post_init__(self) -> None:
        if type(self.policy) is not BomNormalizationPolicy:
            raise NormalizationPolicyError("BOM normalization requires an explicit policy")

    def normalize(
        self, document: MappedDocument, *, provenance: DecisionProvenance
    ) -> tuple[NormalizedObservation, ...]:
        if document.mapping_schema != BOM_TABLE_SCHEMA.reference_id:
            raise NormalizationError("normalization requires the BOM table mapping schema")
        rows: dict[int, set[str]] = {}
        for field in document.fields:
            location = field.evidence.location
            key = re.fullmatch(r"BOM!([A-Z]{1,3})([1-9][0-9]{0,6})", field.field_key)
            if (
                key is None
                or not isinstance(location, TabularLocation)
                or location.sheet != "BOM"
                or int(key[2]) != location.row
            ):
                raise NormalizationError(
                    "BOM normalization requires consistent row/cell field locations"
                )
            column = key[1]
            expected = _COLUMNS.get(column, f"unmapped.{column}")
            if field.field_name != expected or (
                field.raw_value is not None and location.cells != (column,)
            ):
                raise NormalizationError(f"{field.field_key}: field meaning and evidence disagree")
            rows.setdefault(location.row, set()).add(column)
        if any(not _COLUMNS.keys() <= columns for columns in rows.values()):
            raise NormalizationError(
                "BOM normalization requires all four mapped fields per source row"
            )
        source = document.source_document.artifact.source
        observations: list[NormalizedObservation] = []
        for field in document.fields:
            unit = (
                "each"
                if field.field_name == "quantity"
                else (
                    f"{self.policy.currency}/{self.policy.price_unit.value}"
                    if field.field_name == "unit_price"
                    else None
                )
            )
            value = field.raw_value
            status = field.status
            diagnostic = field.diagnostic
            if field.field_name.startswith("unmapped."):
                value, status, diagnostic = (
                    None,
                    EpistemicStatus.UNRESOLVED,
                    "unmapped field cannot be normalized",
                )
            elif value is not None:
                if field.field_name in ("quantity", "unit_price"):
                    value = _decimal(field)
                    if (
                        field.field_name == "quantity"
                        and self.policy.quantity_unit is CountUnit.DOZEN
                    ):
                        # The admitted lexeme has at most 128 digits. This isolated context cannot
                        # round a product by 12, regardless of the caller's Decimal context.
                        value = Context(prec=256).multiply(value, Decimal(12))
                elif not isinstance(value, str):
                    raise NormalizationError(
                        f"{field.field_key}: identifier/description source must be text"
                    )
            observations.append(
                NormalizedObservation(
                    field.field_key,
                    stable_id(
                        "bom-source-row",
                        document.source_document.document_id,
                        field.evidence.sheet,
                        field.evidence.row,
                    ),
                    f"procurement.bom.{field.field_name}",
                    value,
                    unit,
                    field,
                    source.scope,
                    source.observed_at,
                    status,
                    provenance,
                    diagnostic,
                )
            )
        return tuple(observations)
