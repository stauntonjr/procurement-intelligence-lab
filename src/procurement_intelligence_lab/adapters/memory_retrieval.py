"""Dependency-free lexical retrieval projection reference adapter."""

from datetime import datetime

from procurement_intelligence_lab.domain.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.domain.retrieval import (
    ProjectionBuildRequest,
    ProjectionManifest,
    ProjectionStatus,
    RetrievalHit,
    source_entry_ids,
)


class InMemoryLexicalProjection:
    """A rebuildable, derived index; the assertion ledger remains canonical."""

    def __init__(self) -> None:
        self._manifests: dict[str, ProjectionManifest] = {}
        self._entries: dict[str, tuple[AssertionLedgerEntry, ...]] = {}

    def build(
        self,
        entries: tuple[AssertionLedgerEntry, ...],
        *,
        request: ProjectionBuildRequest,
    ) -> ProjectionManifest:
        source_as_of = max(
            (entry.observed_at for entry in entries),
            default=request.requested_at,
        )
        manifest = ProjectionManifest(
            projection_id=request.projection_id,
            kind=request.kind,
            implementation_version=request.implementation_version,
            config_digest=request.config_digest,
            source_entry_ids=source_entry_ids(entries),
            source_as_of=source_as_of,
            status=ProjectionStatus.READY,
            recorded_at=request.requested_at,
        )
        self._entries[request.projection_id] = entries
        self._manifests[request.projection_id] = manifest
        return manifest

    def status(self, projection_id: str) -> ProjectionManifest | None:
        return self._manifests.get(projection_id)

    def search(
        self, projection_id: str, query: str, *, limit: int = 10
    ) -> tuple[RetrievalHit, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        manifest = self._manifests.get(projection_id)
        if manifest is None or manifest.status is not ProjectionStatus.READY:
            raise LookupError("projection is not ready")
        terms = tuple(term for term in query.casefold().split() if term)
        if not terms:
            return ()
        hits: list[RetrievalHit] = []
        for entry in self._entries[projection_id]:
            assertion = entry.assertion
            text = " ".join(
                (assertion.subject_key, assertion.predicate.value, str(assertion.value))
            ).casefold()
            matched = sum(term in text for term in terms)
            if matched:
                hits.append(RetrievalHit(entry, matched / len(terms), manifest.manifest_id))
        return tuple(
            sorted(hits, key=lambda hit: (-hit.score, hit.entry.entry_id))[:limit]
        )

    def fail(
        self, projection_id: str, *, reason: str, recorded_at: datetime
    ) -> ProjectionManifest:
        if recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        previous = self._require_manifest(projection_id)
        self._entries.pop(projection_id, None)
        return self._record(
            previous,
            status=ProjectionStatus.FAILED,
            recorded_at=recorded_at,
            failure_reason=reason,
        )

    def delete(self, projection_id: str, *, recorded_at: datetime) -> ProjectionManifest:
        if recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        previous = self._require_manifest(projection_id)
        self._entries.pop(projection_id, None)
        return self._record(
            previous, status=ProjectionStatus.DELETED, recorded_at=recorded_at
        )

    def _require_manifest(self, projection_id: str) -> ProjectionManifest:
        manifest = self._manifests.get(projection_id)
        if manifest is None:
            raise LookupError("projection does not exist")
        return manifest

    def _record(
        self,
        previous: ProjectionManifest,
        *,
        status: ProjectionStatus,
        recorded_at: datetime,
        failure_reason: str | None = None,
    ) -> ProjectionManifest:
        manifest = ProjectionManifest(
            projection_id=previous.projection_id,
            kind=previous.kind,
            implementation_version=previous.implementation_version,
            config_digest=previous.config_digest,
            source_entry_ids=previous.source_entry_ids,
            source_as_of=previous.source_as_of,
            status=status,
            recorded_at=recorded_at,
            failure_reason=failure_reason,
        )
        self._manifests[previous.projection_id] = manifest
        return manifest
