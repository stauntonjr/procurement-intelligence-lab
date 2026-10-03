"""Repository-owned fixture workflow contract; no framework authority."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from procurement_intelligence_lab.platform.semantics.briefs import ReviewBrief, SavedBrief
from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
)


class WorkflowError(RuntimeError):
    code = ErrorCode.WORKFLOW_UNAVAILABLE
    category = ErrorCategory.INFRASTRUCTURE


class WorkflowBudgetExceeded(WorkflowError):
    code = ErrorCode.WORKFLOW_BUDGET_EXCEEDED
    category = ErrorCategory.POLICY


@dataclass(frozen=True)
class WorkflowRequest:
    item: str
    as_of: datetime

    def __post_init__(self) -> None:
        if type(self.item) is not str or not self.item.strip() or len(self.item) > 100:
            raise SemanticContractError("workflow item must be bounded nonempty text")
        if (
            type(self.as_of) is not datetime
            or self.as_of.tzinfo is None
            or self.as_of.utcoffset() is None
        ):
            raise SemanticContractError("workflow as-of must be timezone aware")


@dataclass(frozen=True)
class WorkflowView:
    run_id: str
    status: Literal["awaiting_review", "ready_to_save", "rejected", "completed"]
    brief: ReviewBrief
    saved: SavedBrief | None
