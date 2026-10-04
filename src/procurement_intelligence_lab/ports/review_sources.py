"""Minimal admitted catalog and source mechanics for a review composition."""

from typing import Protocol

from procurement_intelligence_lab.platform.semantics.scope import RequestContext
from procurement_intelligence_lab.ports.corpus import CorpusSourceLookup


class ReviewSources(CorpusSourceLookup, Protocol):
    def items(self, *, context: RequestContext) -> tuple[str, ...]: ...
    def snapshot_id(self, *, context: RequestContext) -> str: ...

    def source_ids(self, *, context: RequestContext) -> frozenset[str]: ...
