"""Rebuildable retrieval projection contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.platform.semantics.scope import RequestContext


class ProjectionKind(StrEnum):
    LEXICAL = "lexical"
    VECTOR = "vector"
    GRAPH = "graph"


class ProjectionStatus(StrEnum):
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass(frozen=True)
class ProjectionBuildRequest:
    projection_id: str
    kind: ProjectionKind
    implementation_version: str
    config_digest: str
    requested_at: datetime
    scope: RequestContext

    def __post_init__(self) -> None:
        if not self.projection_id:
            raise ValueError("projection_id is required")
        if not self.implementation_version:
            raise ValueError("implementation_version is required")
        if not self.config_digest:
            raise ValueError("config_digest is required")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")


@dataclass(frozen=True)
class ProjectionManifest:
    projection_id: str
    kind: ProjectionKind
    implementation_version: str
    config_digest: str
    source_entry_ids: tuple[str, ...]
    source_as_of: datetime
    status: ProjectionStatus
    recorded_at: datetime
    scope: RequestContext
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.source_as_of.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("projection timestamps must be timezone-aware")
        if self.status is ProjectionStatus.FAILED and not self.failure_reason:
            raise ValueError("failed projections require a failure_reason")
        if self.status is not ProjectionStatus.FAILED and self.failure_reason is not None:
            raise ValueError("only failed projections may carry a failure_reason")

    @property
    def manifest_id(self) -> str:
        return stable_id(
            "projection-manifest",
            self.projection_id,
            self.kind.value,
            self.implementation_version,
            self.config_digest,
            self.source_entry_ids,
            self.source_as_of.isoformat(),
            self.status.value,
            self.recorded_at.isoformat(),
            self.scope.tenant_id,
            self.scope.project_id,
            self.scope.site_id,
            self.failure_reason,
        )


@dataclass(frozen=True)
class RetrievalHit:
    entry: AssertionLedgerEntry
    score: float
    projection_manifest_id: str
    epistemic_status: str = "source_assertion"

    def __post_init__(self) -> None:
        if not 0.0 < self.score <= 1.0:
            raise ValueError("score must be in (0, 1]")


def source_entry_ids(entries: tuple[AssertionLedgerEntry, ...]) -> tuple[str, ...]:
    return tuple(entry.entry_id for entry in entries)
