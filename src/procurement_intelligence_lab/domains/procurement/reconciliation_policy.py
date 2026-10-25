"""Bounded synthetic authority attestations and exact governing-policy content."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from procurement_intelligence_lab.domains.procurement.governance import GoverningSourceType
from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
from procurement_intelligence_lab.platform.execution.identity import (
    aware,
    canonical,
    digest,
    digest_text,
    text,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    OperationAuthorityEvidence,
    ReconciliationPolicyEvidence,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError

AUTHORITY_SCHEMA = "procurement-source-authority/v1"
PARAMETERS = tuple(
    sorted(
        {
            "profile": "retained-resolution-reconciliation/v1",
            "policy_id": "procurement-governing-claims/v1",
            "predicate": "required_quantity",
            "quantity_unit": "each",
        }.items()
    )
)
DECLARATION = "procurement.reconcile/governed-required-quantity@1"


def strict_json(data: bytes, limit: int) -> dict[str, Any]:
    admit(type(data) is bytes and 0 < len(data) <= limit)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in items:
            admit(k not in result)
            result[k] = v
        return result

    def constant(value: str) -> None:
        raise PackageExecutionError("reconciliation JSON requires finite values")

    try:
        raw: object = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
        pending: list[tuple[Any, int]] = [(raw, 0)]
        while pending:
            value, depth = pending.pop()
            admit(depth <= 16)
            if isinstance(value, str):
                value.encode("utf-8")
            elif isinstance(value, dict):
                record = cast(dict[str, Any], value)
                pending.extend((k, depth + 1) for k in record)
                pending.extend((v, depth + 1) for v in record.values())
            elif isinstance(value, list):
                pending.extend((v, depth + 1) for v in cast(list[Any], value))
        admit(type(raw) is dict)
        return cast(dict[str, Any], raw)
    except (ValueError, UnicodeError, RecursionError):
        raise PackageExecutionError(
            "reconciliation input requires bounded unambiguous UTF-8 JSON"
        ) from None


def identifier(value: object, limit: int = 1024) -> str:
    text(value)
    assert isinstance(value, str)
    admit(len(value) <= limit and not any(ord(c) < 32 or ord(c) == 127 for c in value))
    return value


def timestamp(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(identifier(value, 128))
    except ValueError:
        raise PackageExecutionError("reconciliation timestamp requires aware ISO8601") from None
    aware(result)
    return result


@dataclass(frozen=True)
class BomAuthorityRecord:
    execution_digest: str
    artifact_id: str
    content_hash: str
    revision_id: str
    supersedes_revision_ids: tuple[str, ...]
    source_role: GoverningSourceType
    approval_record_ref: str | None
    approved_at: datetime | None
    effective_from: datetime
    effective_until: datetime | None
    document_at: datetime

    def __post_init__(self) -> None:
        digest_text(self.execution_digest)
        digest_text(self.content_hash)
        identifier(self.artifact_id)
        identifier(self.revision_id, 256)
        admit(
            type(self.supersedes_revision_ids) is tuple and len(self.supersedes_revision_ids) <= 8
        )
        for v in self.supersedes_revision_ids:
            identifier(v, 256)
        admit(
            self.supersedes_revision_ids == tuple(sorted(set(self.supersedes_revision_ids)))
            and self.revision_id not in self.supersedes_revision_ids
        )
        admit(type(self.source_role) is GoverningSourceType)
        admit((self.approval_record_ref is None) == (self.approved_at is None))
        if self.approval_record_ref is not None:
            identifier(self.approval_record_ref)
        aware(self.effective_from)
        aware(self.document_at)
        for v in (self.approved_at, self.effective_until):
            if v is not None:
                aware(v)
        admit(self.effective_until is None or self.effective_until > self.effective_from)

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_digest": self.execution_digest,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "revision_id": self.revision_id,
            "supersedes_revision_ids": list(self.supersedes_revision_ids),
            "source_role": self.source_role.value,
            "approval": None
            if self.approved_at is None
            else {
                "record_ref": self.approval_record_ref,
                "approved_at": self.approved_at.isoformat(),
            },
            "effective_from": self.effective_from.isoformat(),
            "effective_until": None
            if self.effective_until is None
            else self.effective_until.isoformat(),
            "document_at": self.document_at.isoformat(),
        }


def _records(data: bytes) -> tuple[BomAuthorityRecord, ...]:
    root = strict_json(data, 65536)
    admit(set(root) == {"schema_version", "producers"} and root["schema_version"] == "1.0")
    values = root["producers"]
    admit(type(values) is list and 1 <= len(values) <= 8)
    out: list[BomAuthorityRecord] = []
    for raw_record in cast(list[Any], values):
        admit(type(raw_record) is dict)
        r = cast(dict[str, Any], raw_record)
        admit(
            type(r) is dict
            and set(r)
            == {
                "execution_digest",
                "artifact_id",
                "content_hash",
                "revision_id",
                "supersedes_revision_ids",
                "source_role",
                "approval",
                "effective_from",
                "effective_until",
                "document_at",
            }
        )
        approval: dict[str, Any] | None = r["approval"]
        admit(
            approval is None
            or (type(approval) is dict and set(approval) == {"record_ref", "approved_at"})
        )
        ids: list[str] = r["supersedes_revision_ids"]
        admit(type(ids) is list and len(ids) <= 8 and all(type(v) is str for v in ids))
        admit(len(set(ids)) == len(ids))
        try:
            role = GoverningSourceType(identifier(r["source_role"]))
        except ValueError:
            raise PackageExecutionError("unsupported authority source role") from None
        out.append(
            BomAuthorityRecord(
                identifier(r["execution_digest"]),
                identifier(r["artifact_id"]),
                identifier(r["content_hash"]),
                identifier(r["revision_id"], 256),
                tuple(sorted(ids)),
                role,
                None if approval is None else identifier(approval["record_ref"]),
                None if approval is None else timestamp(approval["approved_at"]),
                timestamp(r["effective_from"]),
                None if r["effective_until"] is None else timestamp(r["effective_until"]),
                timestamp(r["document_at"]),
            )
        )
    admit(
        len({r.execution_digest for r in out}) == len(out)
        and len({r.revision_id for r in out}) == len(out)
    )
    return tuple(sorted(out, key=lambda r: r.execution_digest))


def _semantic(records: tuple[BomAuthorityRecord, ...]) -> bytes:
    return json.dumps(
        {"schema_version": "1.0", "producers": [r.as_dict() for r in records]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class BomAuthorityInput:
    evidence: OperationAuthorityEvidence
    records: tuple[BomAuthorityRecord, ...]

    def __post_init__(self) -> None:
        admit(
            type(self.evidence) is OperationAuthorityEvidence
            and self.evidence.schema_id == AUTHORITY_SCHEMA
        )
        admit(
            type(self.records) is tuple and all(type(r) is BomAuthorityRecord for r in self.records)
        )
        admit(
            canonical(_records(self.evidence.raw_json)) == canonical(self.records)
            and _semantic(self.records) == self.evidence.semantic_json
        )


def load_bom_authority(data: bytes) -> BomAuthorityInput:
    records = _records(data)
    return BomAuthorityInput(
        OperationAuthorityEvidence(AUTHORITY_SCHEMA, data, _semantic(records)), records
    )


@dataclass(frozen=True)
class BomReconciliationPolicy:
    evidence: ReconciliationPolicyEvidence

    def __post_init__(self) -> None:
        admit(
            type(self.evidence) is ReconciliationPolicyEvidence
            and self.evidence.parameters == PARAMETERS
        )
        admit(
            self.evidence.reference
            == ResolvedReference(
                DECLARATION, "procurement-governing-claims/v1", digest(dict(PARAMETERS))
            )
        )

    @classmethod
    def from_data(cls, data: bytes) -> "BomReconciliationPolicy":
        values = strict_json(data, 32768)
        admit(values == dict(PARAMETERS))
        return cls(
            ReconciliationPolicyEvidence(
                ResolvedReference(DECLARATION, "procurement-governing-claims/v1", digest(values)),
                PARAMETERS,
            )
        )
