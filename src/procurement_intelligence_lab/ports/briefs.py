"""Application-owned exact brief persistence boundary."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from procurement_intelligence_lab.platform.semantics.briefs import (
    ReviewBrief,
    ReviewReceipt,
    SavedBrief,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext


class BriefStore(Protocol):
    def put(self, brief: ReviewBrief, *, context: RequestContext) -> None: ...
    def get(self, run_id: str, brief_id: str | None, *, context: RequestContext) -> ReviewBrief: ...
    def decide(self, receipt: ReviewReceipt, *, context: RequestContext) -> ReviewReceipt: ...
    def save(
        self, brief: ReviewBrief, clock: Callable[[], datetime], *, context: RequestContext
    ) -> SavedBrief: ...
