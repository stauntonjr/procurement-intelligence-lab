"""Immutable application review authority, independent of graph checkpoints."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import cast

from procurement_intelligence_lab.platform.semantics.agent_runs import AgentRun, run_dto
from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    PolicyContractError,
    SemanticContractError,
)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _text(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 200:
        raise SemanticContractError("review identifiers require bounded nonempty strings")


def _aware(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise SemanticContractError("review clock must be timezone aware")


class BriefConflict(PolicyContractError):
    code = ErrorCode.BRIEF_REVIEW_CONFLICT
    category = ErrorCategory.POLICY


class BriefIntegrityError(RuntimeError):
    code = ErrorCode.BRIEF_STORE_UNAVAILABLE
    category = ErrorCategory.INFRASTRUCTURE


class BriefNotFound(SemanticContractError):
    code = ErrorCode.BRIEF_NOT_FOUND
    category = ErrorCategory.INPUT


@dataclass(frozen=True)
class ReviewBrief:
    brief_id: str
    run: AgentRun
    version: int
    item: str
    as_of: datetime
    snapshot_id: str
    content_json: str
    created_at: datetime

    def __post_init__(self) -> None:
        for value in (self.brief_id, self.item, self.snapshot_id):
            _text(value)
        if type(self.run) is not AgentRun or type(self.version) is not int or self.version < 1:
            raise SemanticContractError("brief requires immutable run and positive version")
        _aware(self.as_of)
        _aware(self.created_at)
        if self.created_at < self.run.created_at:
            raise SemanticContractError("brief cannot precede run")
        if type(self.content_json) is not str or len(self.content_json) > 2_000_000:
            raise SemanticContractError("brief requires bounded canonical facts")
        try:
            value = json.loads(self.content_json)
        except ValueError as error:
            raise SemanticContractError("brief facts must be valid JSON") from error
        if (
            not isinstance(value, dict)
            or canonical(cast(dict[str, object], value)) != self.content_json
        ):
            raise SemanticContractError("brief facts must be a canonical JSON object")

    @property
    def digest(self) -> str:
        return sha256(canonical(brief_dto(self, include_digest=False)).encode()).hexdigest()

    @property
    def idempotency_key(self) -> str:
        return "brief-save:" + self.digest


@dataclass(frozen=True)
class ReviewReceipt:
    brief_id: str
    run_id: str
    digest: str
    reviewer_id: str
    decision: str
    reviewed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for value in (self.brief_id, self.run_id, self.digest, self.reviewer_id):
            _text(value)
        if len(self.digest) != 64 or any(c not in "0123456789abcdef" for c in self.digest):
            raise SemanticContractError("receipt requires SHA256 brief digest")
        if type(self.decision) is not str or self.decision not in ("approve", "reject"):
            raise SemanticContractError("review decision must be approve or reject")
        _aware(self.reviewed_at)
        _aware(self.expires_at)
        if self.expires_at <= self.reviewed_at:
            raise SemanticContractError("review expiry must follow review time")


@dataclass(frozen=True)
class SavedBrief:
    saved_id: str
    brief_id: str
    run_id: str
    digest: str
    idempotency_key: str
    saved_at: datetime

    def __post_init__(self) -> None:
        for value in (self.saved_id, self.brief_id, self.run_id, self.digest, self.idempotency_key):
            _text(value)
        _aware(self.saved_at)
        if len(self.digest) != 64 or any(c not in "0123456789abcdef" for c in self.digest):
            raise SemanticContractError("saved result requires SHA256 digest")
        if self.idempotency_key != "brief-save:" + self.digest:
            raise SemanticContractError("saved key must bind exact brief digest")


def brief_dto(brief: ReviewBrief, *, include_digest: bool = True) -> dict[str, object]:
    data: dict[str, object] = {
        "brief_id": brief.brief_id,
        "run": run_dto(brief.run),
        "version": brief.version,
        "item": brief.item,
        "as_of": brief.as_of.isoformat(),
        "snapshot_id": brief.snapshot_id,
        "content_json": brief.content_json,
        "created_at": brief.created_at.isoformat(),
    }
    if include_digest:
        data.update(digest=brief.digest, idempotency_key=brief.idempotency_key)
    return data
