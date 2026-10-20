"""Strict policy loading at the CLI boundary; domain meaning stays in procurement."""

import json
from pathlib import Path
from typing import cast

from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.errors import NormalizationPolicyError


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise NormalizationPolicyError("normalization policy contains duplicate keys")
        result[key] = value
    return result


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise NormalizationPolicyError("normalization policy values must be text")
    return value


def load_policy(path: Path) -> BomNormalizationPolicy:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise NormalizationPolicyError(
            "normalization policy must be readable unambiguous UTF-8 JSON"
        ) from None
    if not isinstance(value, dict):
        raise NormalizationPolicyError("normalization policy must be an object")
    data = cast(dict[str, object], value)
    if set(data) != {
        "profile",
        "quantity_unit",
        "currency",
        "price_unit",
    }:
        raise NormalizationPolicyError(
            "normalization policy requires profile, quantity_unit, currency and price_unit only"
        )
    if (
        any(not isinstance(value, str) for value in data.values())
        or data["profile"] != "bom-decimal@1"
    ):
        raise NormalizationPolicyError(
            "unsupported normalization profile or non-text policy values"
        )
    try:
        quantity_unit, price_unit = (
            CountUnit(_text(data["quantity_unit"])),
            CountUnit(_text(data["price_unit"])),
        )
    except ValueError:
        raise NormalizationPolicyError("normalization units must be each or dozen") from None
    return BomNormalizationPolicy(quantity_unit, _text(data["currency"]), price_unit)
