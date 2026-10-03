"""Read-only, domain-neutral admitted source inventory."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import ClassVar, Protocol

from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.scope import RequestContext, StateScope


class CorpusAdmissionError(ValueError):
    """Runtime inputs cannot be admitted; never a business absence."""

    code: ClassVar[str] = "corpus_admission_failed"
    category: ClassVar[str] = "infrastructure"


class CorpusNotFoundError(LookupError):
    """Authorized item or evidence is absent from the admitted inventory."""

    code: ClassVar[str] = "not_found"
    category: ClassVar[str] = "input"


@dataclass(frozen=True)
class CorpusFact:
    canonical_key: str
    quantity: Decimal
    unit: str
    role: str
    scope: StateScope
    revision_id: str
    supersedes: tuple[str, ...]
    approved_at: datetime | None
    effective_from: datetime
    effective_until: datetime | None
    document_at: datetime
    ingested_at: datetime
    line_id: str
    assertion_id: str
    evidence: EvidenceRef
    authority: EvidenceRef


@dataclass(frozen=True)
class CorpusInventory:
    snapshot_id: str
    facts: tuple[CorpusFact, ...]


@dataclass(frozen=True)
class CorpusSourceRow:
    evidence: EvidenceRef
    headers: tuple[str, ...]
    cells: tuple[str, ...]
    highlighted_columns: tuple[str, ...]


@dataclass(frozen=True)
class CorpusSourceRecord:
    evidence: EvidenceRef
    # Canonical immutable JSON for the original authority record and document metadata.
    record_json: str


class CorpusReader(Protocol):
    def inventory(self, *, context: RequestContext) -> CorpusInventory: ...

    def source(
        self, evidence: EvidenceRef, *, context: RequestContext
    ) -> CorpusSourceRow | CorpusSourceRecord: ...


class CorpusSourceLookup(Protocol):
    """Resolve a scoped opaque source ID with one fresh admission."""

    def source_by_id(
        self, evidence_id: str, *, context: RequestContext
    ) -> CorpusSourceRow | CorpusSourceRecord: ...
