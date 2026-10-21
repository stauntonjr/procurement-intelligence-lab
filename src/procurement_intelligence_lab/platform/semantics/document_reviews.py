"""Evidence-bound document reviews; accepted corrections do not rewrite source facts."""

import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import cast

from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.errors import ReviewContractError
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.values import SemanticValue

POLICY = "document-value-review/v1"


class ReviewWorkflow(StrEnum):
    DOCUMENT_VALUE = "document_value"
    ENTITY = "entity"
    OPERATIONAL = "operational"


class ReviewOutcome(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


def unicode_text(value: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ReviewContractError("review text must contain valid Unicode scalar values") from None


def text(value: str, limit: int = 500) -> None:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ReviewContractError("review text must be bounded and nonempty")
    unicode_text(value)


def aware(value: datetime) -> None:
    if type(value) is not datetime or not isinstance(value.tzinfo, timezone):
        raise ReviewContractError("review time requires an aware fixed-offset datetime")


def _identity(value: object) -> object:
    """Type-tag complete immutable content for exact review binding, never a decoder."""
    if value is None:
        return ["null"]
    if type(value) in (str, int, bool):
        return [type(value).__name__, value]
    if isinstance(value, StrEnum):
        return ["enum", type(value).__name__, value.value]
    if type(value) is Decimal:
        return ["decimal", str(value)]
    if isinstance(value, (date, datetime)):
        return [type(value).__name__, value.isoformat()]
    if isinstance(value, tuple):
        return ["tuple", [_identity(x) for x in cast(tuple[object, ...], value)]]
    if is_dataclass(value) and not isinstance(value, type):
        return [
            type(value).__name__,
            [[f.name, _identity(getattr(value, f.name))] for f in fields(value)],
        ]
    raise ReviewContractError("unsupported review identity value")


@dataclass(frozen=True)
class ReviewProposal:
    scope: StateScope
    request_id: str
    snapshot_id: str
    previous: SourceAssertion
    proposed_value: SemanticValue | None
    reason: str
    proposer_id: str
    workflow: ReviewWorkflow = ReviewWorkflow.DOCUMENT_VALUE

    def __post_init__(self) -> None:
        for value in (self.request_id, self.snapshot_id, self.proposer_id):
            text(value)
        text(self.reason, 2000)
        for value in (
            self.scope.tenant_id,
            self.scope.project_id,
            self.scope.site_id,
            self.scope.version,
        ):
            text(value)
        if self.workflow is not ReviewWorkflow.DOCUMENT_VALUE:
            raise ReviewContractError("only document_value review is supported")
        if type(self.previous) is not SourceAssertion or self.previous.context is None:
            raise ReviewContractError("document review requires a source assertion with context")
        if self.previous.context.origin.artifact.source.scope != self.scope:
            raise ReviewContractError("document review requires exact source scope/version")
        value = self.proposed_value
        if value is not None and type(value) not in (str, bool, int, Decimal, date, datetime):
            raise ReviewContractError("unsupported proposed value type")
        if type(value) is str:
            unicode_text(value)
        if type(value) is Decimal and not value.is_finite():
            raise ReviewContractError("proposed decimal must be finite")
        if type(value) is datetime:
            aware(value)

    @property
    def task_id(self) -> str:
        return stable_id("document-review-task-v1", self.scope, self.request_id)


@dataclass(frozen=True)
class DocumentReviewTask:
    proposal: ReviewProposal
    recorded_at: datetime
    policy_reference: str = POLICY

    def __post_init__(self) -> None:
        if type(self.proposal) is not ReviewProposal or self.policy_reference != POLICY:
            raise ReviewContractError("task requires the supported immutable proposal/policy")
        aware(self.recorded_at)
        context = self.proposal.previous.context
        if context is None or self.recorded_at < context.origin.recorded_at:
            raise ReviewContractError("review task cannot precede source recording")

    @property
    def task_id(self) -> str:
        return self.proposal.task_id

    @property
    def digest(self) -> str:
        raw = json.dumps(
            [POLICY, _identity(self)], sort_keys=True, ensure_ascii=True, separators=(",", ":")
        )
        return sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ReviewDecisionCommand:
    scope: StateScope
    request_id: str
    task_id: str
    task_digest: str
    outcome: ReviewOutcome
    reviewer_id: str
    reason: str

    def __post_init__(self) -> None:
        for value in (self.request_id, self.task_id, self.reviewer_id):
            text(value)
        text(self.reason, 2000)
        if (
            type(self.task_digest) is not str
            or len(self.task_digest) != 64
            or any(c not in "0123456789abcdef" for c in self.task_digest)
        ):
            raise ReviewContractError("decision requires exact SHA256 task digest")
        if type(self.outcome) is not ReviewOutcome:
            raise ReviewContractError("decision requires approve or reject outcome")

    @property
    def decision_id(self) -> str:
        return stable_id("document-review-decision-v1", self.scope, self.request_id)


@dataclass(frozen=True)
class DocumentReviewDecision:
    command: ReviewDecisionCommand
    recorded_at: datetime

    def __post_init__(self) -> None:
        if type(self.command) is not ReviewDecisionCommand:
            raise ReviewContractError("decision requires an immutable review command")
        aware(self.recorded_at)

    @property
    def effective_at(self) -> datetime:
        return self.recorded_at

    @property
    def decision_id(self) -> str:
        return self.command.decision_id


@dataclass(frozen=True)
class ReviewHistory:
    task: DocumentReviewTask
    decision: DocumentReviewDecision | None

    def __post_init__(self) -> None:
        if type(self.task) is not DocumentReviewTask or (
            self.decision is not None and type(self.decision) is not DocumentReviewDecision
        ):
            raise ReviewContractError("history requires an immutable task and optional decision")
        if self.decision is not None:
            command = self.decision.command
            if (
                command.scope != self.task.proposal.scope
                or command.task_id != self.task.task_id
                or command.task_digest != self.task.digest
                or self.decision.recorded_at < self.task.recorded_at
            ):
                raise ReviewContractError(
                    "review decision must bind exact task, scope and prospective time"
                )

    @property
    def digest(self) -> str:
        """Bind complete retained task/decision content, including timestamp encoding."""
        raw = json.dumps(_identity(self), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return sha256(raw.encode()).hexdigest()

    @property
    def correction_id(self) -> str | None:
        if self.decision is None or self.decision.command.outcome is not ReviewOutcome.APPROVE:
            return None
        return stable_id(
            "document-correction-v1", self.task.task_id, self.task.digest, self.decision.decision_id
        )
