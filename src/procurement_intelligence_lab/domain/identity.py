"""Deterministic identifiers for evidence-backed domain objects."""

from __future__ import annotations

import json
from hashlib import sha256


def stable_id(namespace: str, *parts: object) -> str:
    """Return a stable, opaque identifier for a semantic object."""
    payload = json.dumps(
        [namespace, *parts],
        ensure_ascii=True,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    digest = sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"
