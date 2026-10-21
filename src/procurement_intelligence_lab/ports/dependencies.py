"""Immutable producer declarations, independent of storage mechanics."""

from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.semantics.dependencies import (
    DependencyManifest,
    DependencySnapshot,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class DependencyStore(Protocol):
    def append(
        self, manifest: DependencyManifest, recorder_id: str, recorded_at: datetime
    ) -> DependencySnapshot: ...
    def get(self, scope: StateScope, snapshot_id: str) -> DependencySnapshot: ...
