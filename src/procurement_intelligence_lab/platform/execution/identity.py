"""Full encoded identities and strict portable execution-boundary primitives."""

import json
import re
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import cast

from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError


def text(value: object) -> None:
    if type(value) is not str or not value or value != value.strip() or len(value) > 4096:
        raise PackageExecutionError("execution identity requires bounded non-empty text")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise PackageExecutionError("execution text must be valid Unicode") from None


def aware(value: object) -> None:
    if type(value) is not datetime or not isinstance(value.tzinfo, timezone):
        raise PackageExecutionError("execution times require aware fixed-offset datetimes")


def digest_text(value: object) -> None:
    if type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value):
        raise PackageExecutionError("execution digest must be lowercase SHA256")


def encoded(value: object) -> object:
    if isinstance(value, Enum):
        return encoded(value.value)
    if type(value) is datetime:
        aware(value)
        return value.isoformat()
    if type(value) is date:
        return value.isoformat()
    if type(value) is Decimal:
        if not value.is_finite():
            raise PackageExecutionError("non-finite execution value")
        return str(value)
    if type(value) is bytes:
        return value.hex()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: encoded(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [encoded(v) for v in cast(tuple[object, ...], value)]
    if isinstance(value, dict):
        data = cast(dict[object, object], value)
        if any(type(k) is not str for k in data):
            raise PackageExecutionError("execution object keys must be text")
        return {cast(str, k): encoded(v) for k, v in data.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise PackageExecutionError("unsupported execution identity value")


def canonical(value: object) -> bytes:
    try:
        return json.dumps(
            encoded(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (UnicodeError, ValueError, RecursionError):
        raise PackageExecutionError("invalid execution identity encoding") from None


def digest(value: object) -> str:
    return sha256(canonical(value)).hexdigest()


def same(left: object, right: object) -> bool:
    return type(left) is type(right) and canonical(left) == canonical(right)
