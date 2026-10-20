"""Local byte capture and explicitly process-local content retention."""

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urlsplit

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.errors import (
    ArtifactContentError,
    ArtifactSourceError,
    SourceReferenceError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class MemoryArtifactContent:
    """A synchronous test/development adapter; not durable storage or an authorization boundary."""

    _content: dict[str, bytes] = field(
        default_factory=lambda: dict[str, bytes](), init=False, repr=False
    )

    def put(self, content: bytes) -> str:
        if not isinstance(cast(object, content), bytes):
            raise ArtifactContentError("captured content must be immutable bytes")
        digest = sha256(content).hexdigest()
        if digest in self._content and self._content[digest] != content:
            raise ArtifactContentError("captured content conflicts with its hash")
        self._content[digest] = content
        return digest

    def get(self, content_hash: str) -> bytes:
        try:
            content = self._content[content_hash]
        except KeyError:
            raise ArtifactContentError("captured content is not available") from None
        if sha256(content).hexdigest() != content_hash:
            raise ArtifactContentError("captured content hash mismatch")
        return content


@dataclass(frozen=True)
class LocalFileIngest:
    store: ArtifactContentStore
    captured_at: datetime
    media_type: str = XLSX_MEDIA_TYPE

    def ingest(
        self, source: SourceReference, *, provenance: DecisionProvenance
    ) -> tuple[Artifact, ...]:
        if self.captured_at.tzinfo is None or self.captured_at < source.observed_at:
            raise TemporalContractError(
                "capture must be timezone-aware and not precede observation"
            )
        try:
            uri = urlsplit(source.source_uri)
            if (
                uri.scheme != "file"
                or uri.netloc
                or uri.query
                or uri.fragment
                or not uri.path.startswith("/")
            ):
                raise SourceReferenceError(
                    "local capture requires an absolute file URI without authority, query or fragment"
                )
            decoded = unquote(uri.path, errors="strict")
            if "\x00" in decoded:
                raise SourceReferenceError("local source URI contains an invalid path")
            path = Path(decoded)
        except (ValueError, UnicodeError):
            raise SourceReferenceError("local capture requires a valid local file URI") from None
        try:
            content = path.read_bytes()
        except OSError:
            raise ArtifactSourceError("local source bytes could not be read") from None
        digest = sha256(content).hexdigest()
        if self.store.put(content) != digest:
            raise ArtifactContentError("content store returned an inconsistent capture hash")
        return (
            Artifact(source, digest, self.media_type, len(content), self.captured_at, provenance),
        )
