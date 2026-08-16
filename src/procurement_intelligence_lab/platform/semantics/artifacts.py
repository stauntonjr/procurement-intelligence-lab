"""Universal source-reference and immutable artifact-capture contracts."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class SourceReference:
    source_system: str
    source_uri: str
    scope: StateScope
    observed_at: datetime
    source_version: str | None = None

    def __post_init__(self) -> None:
        if not self.source_system.strip() or not self.source_uri.strip():
            raise SemanticContractError("source system and URI are required")
        if self.observed_at.tzinfo is None:
            raise TemporalContractError("source observed_at must be timezone-aware")
        if self.source_version is not None and not self.source_version.strip():
            raise SemanticContractError("source_version must be non-empty when present")

    @property
    def reference_id(self) -> str:
        return stable_id(
            "source-reference",
            self.source_system,
            self.source_uri,
            self.scope,
            self.observed_at.isoformat(),
            self.source_version,
        )


@dataclass(frozen=True)
class Artifact:
    source: SourceReference
    content_hash: str
    media_type: str
    byte_length: int
    captured_at: datetime
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if not self.content_hash.strip() or not self.media_type.strip():
            raise SemanticContractError("artifact content hash and media type are required")
        if self.byte_length < 0:
            raise SemanticContractError("artifact byte length must be non-negative")
        if self.captured_at.tzinfo is None:
            raise TemporalContractError("artifact captured_at must be timezone-aware")
        if self.captured_at < self.source.observed_at:
            raise TemporalContractError("artifact capture cannot precede source observation")

    @property
    def artifact_id(self) -> str:
        return stable_id(
            "artifact",
            self.source.reference_id,
            self.content_hash,
            self.media_type,
            self.byte_length,
            self.captured_at.isoformat(),
            self.provenance.provenance_id,
        )
