"""Atomic source snapshot materialization, distinct from single-assertion append."""

from typing import Protocol

from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt, DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class AssertionArchive(Protocol):
    def append(self, snapshot: DocumentSnapshot, content: bytes) -> ArchiveReceipt: ...
    def load(
        self, scope: StateScope, snapshot_id: str
    ) -> tuple[ArchiveReceipt, DocumentSnapshot]: ...
    def history(self, scope: StateScope) -> tuple[ArchiveReceipt, ...]: ...
    def content(self, scope: StateScope, snapshot_id: str) -> bytes: ...
