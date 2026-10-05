"""Closed model proposals and redacted inference attempt records."""

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
    SemanticTypeContractError,
)

ProposalStatus = Literal["investigate", "clarify", "unsupported"]
CallStatus = Literal["pending", "investigate", "clarify", "unsupported", "failed"]
REASONS = frozenset({"none", "item_ambiguous", "date_ambiguous", "unsupported"})


class ModelFailure(RuntimeError):
    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.WORKFLOW_UNAVAILABLE

    def __init__(self, reason: str) -> None:
        if reason not in {
            "model_unavailable",
            "model_timeout",
            "invalid_model_response",
            "invalid_model_output",
            "interpretation_store_unavailable",
        }:
            raise SemanticContractError("unsupported model failure")
        self.reason = reason
        super().__init__(reason)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticContractError("duplicate JSON field")
        result[key] = value
    return result


@dataclass(frozen=True)
class ModelReply:
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None

    def __post_init__(self) -> None:
        if type(self.text) is not str or len(self.text) > 8192:
            raise SemanticContractError("bounded model content required")
        for count in (self.prompt_tokens, self.completion_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise SemanticContractError("nonnegative token counts or unknown required")


@dataclass(frozen=True)
class QuestionProposal:
    status: ProposalStatus
    item: str | None
    project: str
    as_of: datetime | None
    reason: str

    @classmethod
    def parse(cls, raw: str) -> "QuestionProposal":
        value: object = json.loads(raw, object_pairs_hook=_unique)
        if not isinstance(value, dict):
            raise SemanticTypeContractError("proposal must be an object")
        data = cast(dict[str, object], value)
        if set(data) != {"status", "item", "project", "as_of", "reason"}:
            raise SemanticContractError("exact proposal fields required")
        status, item, project, date, reason = (
            data[k] for k in ("status", "item", "project", "as_of", "reason")
        )
        if (
            status not in ("investigate", "clarify", "unsupported")
            or not isinstance(project, str)
            or not project
            or len(project) > 100
        ):
            raise SemanticContractError("closed status and project required")
        if reason not in REASONS or not isinstance(reason, str):
            raise SemanticContractError("closed reason required")
        if status == "investigate":
            if (
                not isinstance(item, str)
                or not item
                or len(item) > 100
                or not isinstance(date, str)
                or reason != "none"
            ):
                raise SemanticContractError("investigation requires exact item/date")
            parsed = datetime.fromisoformat(date)
            if parsed.utcoffset() is None:
                raise SemanticContractError("aware date required")
            return cls("investigate", item, project, parsed, reason)
        if item is not None or date is not None:
            raise SemanticContractError("abstention cannot supply tool arguments")
        if (status == "clarify" and reason not in ("item_ambiguous", "date_ambiguous")) or (
            status == "unsupported" and reason != "unsupported"
        ):
            raise SemanticContractError("reason contradicts status")
        return cls(cast(ProposalStatus, status), None, project, None, reason)


@dataclass(frozen=True)
class InterpretationCall:
    run_id: str
    question_hash: str
    as_of: datetime
    status: CallStatus = "pending"
    item: str | None = None
    reason: str = "none"
    elapsed_seconds: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    def __post_init__(self) -> None:
        if type(self.run_id) is not str or not self.run_id or len(self.run_id) > 200:
            raise SemanticContractError("run identity required")
        if len(self.question_hash) != 64 or any(
            c not in "0123456789abcdef" for c in self.question_hash
        ):
            raise SemanticContractError("question hash required")
        if self.as_of.utcoffset() is None:
            raise SemanticContractError("aware as-of required")
        if self.status not in ("pending", "investigate", "clarify", "unsupported", "failed"):
            raise SemanticContractError("closed call status required")
        if (self.status == "investigate") != (isinstance(self.item, str) and bool(self.item)):
            raise SemanticContractError("only accepted interpretation has item")
        if self.status == "pending":
            if self.reason != "none" or any(
                x is not None
                for x in (self.elapsed_seconds, self.prompt_tokens, self.completion_tokens)
            ):
                raise SemanticContractError("pending outcome and usage are unknown")
        else:
            if (
                type(self.elapsed_seconds) not in (int, float)
                or self.elapsed_seconds is None
                or not math.isfinite(self.elapsed_seconds)
                or self.elapsed_seconds < 0
            ):
                raise SemanticContractError("completed attempt needs measured elapsed time")
            if self.status == "failed":
                ModelFailure(self.reason)
            elif (
                (self.status == "investigate" and self.reason != "none")
                or (
                    self.status == "clarify"
                    and self.reason not in ("item_ambiguous", "date_ambiguous")
                )
                or (self.status == "unsupported" and self.reason != "unsupported")
            ):
                raise SemanticContractError("reason contradicts outcome")
        for count in (self.prompt_tokens, self.completion_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise SemanticContractError("nonnegative token usage or unknown required")
