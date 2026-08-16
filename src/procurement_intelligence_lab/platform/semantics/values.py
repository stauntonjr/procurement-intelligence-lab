"""Portable scalar values used by stage contracts."""

from datetime import date, datetime
from decimal import Decimal

from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)

type SemanticValue = str | bool | int | Decimal | date | datetime


def validate_semantic_value(value: SemanticValue) -> None:
    """Reject values that cannot have stable cross-runtime meaning."""

    if isinstance(value, Decimal) and not value.is_finite():
        raise SemanticContractError("decimal semantic values must be finite")
    if isinstance(value, datetime) and value.tzinfo is None:
        raise TemporalContractError("datetime semantic values must be timezone-aware")
