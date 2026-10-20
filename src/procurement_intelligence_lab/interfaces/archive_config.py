"""Strict local archive configuration; connection strings never enter public payloads."""

import json
import os
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def configured_dsn() -> str:
    dsn = os.environ.get("PIL_ASSERTION_ARCHIVE_DSN", "")
    if not dsn.strip():
        raise ArchiveContractError("PIL_ASSERTION_ARCHIVE_DSN must be configured")
    return dsn


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate scope key")
        data[key] = value
    return data


def load_scope(path: Path) -> StateScope:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
        if not isinstance(value, dict):
            raise TypeError("scope object")
        data = cast(dict[str, Any], value)
        if set(data) != {
            "tenant_id",
            "project_id",
            "site_id",
            "version",
        }:
            raise ValueError("scope fields")
        if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in data.values()):
            raise ValueError("scope text")
        return StateScope(**data)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        raise ArchiveContractError(
            "scope requires unambiguous UTF-8 JSON with four nonempty scope strings"
        ) from None
