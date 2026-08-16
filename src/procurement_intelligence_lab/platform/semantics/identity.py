"""Deterministic identifiers for evidence-backed semantic objects."""

from __future__ import annotations

import json
from hashlib import sha256

from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError


def stable_id(namespace: str, *parts: object) -> str:
    """Return a stable, opaque identifier for a semantic object."""
    if not namespace:
        raise SemanticContractError("identity namespace must not be empty")
    payload = json.dumps(
        [namespace, *parts],
        ensure_ascii=True,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    digest = sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"
