"""Typed evidence locations and evidence-backed result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.identity import stable_id


@runtime_checkable
class EvidenceLocation(Protocol):
    """A source-format-specific locator with deterministic identity parts."""

    @property
    def location_kind(self) -> str: ...

    def identity_parts(self) -> tuple[object, ...]: ...

    def payload_fields(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class TabularLocation:
    """A one-based row and selected cells in a named tabular section."""

    sheet: str
    row: int
    cells: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.sheet:
            raise ValueError("tabular evidence sheet must not be empty")
        if self.row < 1:
            raise ValueError("tabular evidence row must be one-based")
        if not self.cells or any(not cell for cell in self.cells):
            raise ValueError("tabular evidence cells must not be empty")
        if len(set(self.cells)) != len(self.cells):
            raise ValueError("tabular evidence cells must not contain duplicates")

    @property
    def location_kind(self) -> str:
        return "tabular"

    def identity_parts(self) -> tuple[object, ...]:
        # Keep the established evidence ID representation stable.
        return (self.sheet, self.row, self.cells)

    def payload_fields(self) -> dict[str, object]:
        return {"sheet": self.sheet, "row": self.row, "cells": self.cells}


@dataclass(frozen=True)
class RecordLocation:
    """A record key within a named collection or stream."""

    collection: str
    record_key: str

    def __post_init__(self) -> None:
        if not self.collection or not self.record_key:
            raise ValueError("record evidence collection and key are required")

    @property
    def location_kind(self) -> str:
        return "record"

    def identity_parts(self) -> tuple[object, ...]:
        return (self.location_kind, self.collection, self.record_key)

    def payload_fields(self) -> dict[str, object]:
        return {"collection": self.collection, "record_key": self.record_key}


@dataclass(frozen=True, init=False)
class EvidenceRef:
    """Immutable artifact identity plus a typed location within that artifact.

    The legacy tabular constructor remains accepted during the package migration:
    ``EvidenceRef(artifact, hash, sheet, row, cells)``. New code should pass a
    concrete ``EvidenceLocation``.
    """

    artifact_id: str
    content_hash: str
    location: EvidenceLocation

    def __init__(
        self,
        artifact_id: str,
        content_hash: str,
        location: object,
        row: int | None = None,
        cells: tuple[str, ...] | None = None,
    ) -> None:
        artifact_id = artifact_id.strip()
        content_hash = content_hash.strip()
        if not artifact_id or not content_hash:
            raise ValueError("evidence artifact ID and content hash are required")
        resolved_location: EvidenceLocation
        if isinstance(location, str):
            if row is None or cells is None:
                raise ValueError("legacy tabular evidence requires row and cells")
            resolved_location = TabularLocation(location, row, cells)
        else:
            if row is not None or cells is not None:
                raise ValueError("typed evidence location cannot be combined with row or cells")
            if not isinstance(location, EvidenceLocation):
                raise TypeError("location must implement EvidenceLocation")
            resolved_location = location
        object.__setattr__(self, "artifact_id", artifact_id)
        object.__setattr__(self, "content_hash", content_hash)
        object.__setattr__(self, "location", resolved_location)

    @property
    def evidence_id(self) -> str:
        return stable_id(
            "evidence",
            self.artifact_id,
            self.content_hash,
            *self.location.identity_parts(),
        )

    @property
    def sheet(self) -> str:
        if not isinstance(self.location, TabularLocation):
            raise TypeError("evidence does not have a tabular sheet")
        return self.location.sheet

    @property
    def row(self) -> int:
        if not isinstance(self.location, TabularLocation):
            raise TypeError("evidence does not have a tabular row")
        return self.location.row

    @property
    def cells(self) -> tuple[str, ...]:
        if not isinstance(self.location, TabularLocation):
            raise TypeError("evidence does not have tabular cells")
        return self.location.cells

    def as_dict(self) -> dict[str, object]:
        """Return a stable public payload with typed and legacy tabular fields."""
        payload: dict[str, object] = {
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "location_kind": self.location.location_kind,
            "evidence_id": self.evidence_id,
        }
        location_fields = self.location.payload_fields()
        reserved = location_fields.keys() & payload.keys()
        if reserved:
            raise ValueError(
                f"evidence location payload uses reserved fields: {sorted(reserved)!r}"
            )
        payload.update(location_fields)
        return payload


@dataclass(frozen=True)
class EvidenceBackedResult[ValueT]:
    value: ValueT | None
    evidence: tuple[EvidenceRef, ...]
    status: EpistemicStatus

    def __post_init__(self) -> None:
        if self.status is EpistemicStatus.UNRESOLVED and self.value is not None:
            raise ValueError("unresolved results must not carry a resolved value")
