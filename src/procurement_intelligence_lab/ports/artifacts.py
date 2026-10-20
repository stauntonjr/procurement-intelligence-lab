"""Captured byte storage independent of source transport, domain and durability."""

from typing import Protocol


class ArtifactContentStore(Protocol):
    """Immutable content addressed by its SHA-256; missing content fails explicitly."""

    def put(self, content: bytes) -> str: ...

    def get(self, content_hash: str) -> bytes: ...
