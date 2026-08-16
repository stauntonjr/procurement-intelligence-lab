"""Outbound ports for rebuildable retrieval projections."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.semantics.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.platform.semantics.retrieval import (
    ProjectionBuildRequest,
    ProjectionManifest,
    RetrievalHit,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext


class RetrievalProjection(Protocol):
    """A derived index built only from canonical assertion-ledger entries."""

    def build(
        self,
        entries: tuple[AssertionLedgerEntry, ...],
        *,
        request: ProjectionBuildRequest,
    ) -> ProjectionManifest: ...

    def status(self, projection_id: str) -> ProjectionManifest | None: ...

    def search(
        self, projection_id: str, query: str, *, context: RequestContext, limit: int = 10
    ) -> tuple[RetrievalHit, ...]: ...

    def fail(
        self, projection_id: str, *, reason: str, recorded_at: datetime
    ) -> ProjectionManifest: ...

    def delete(self, projection_id: str, *, recorded_at: datetime) -> ProjectionManifest: ...
