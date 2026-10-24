"""Bounded portable candidate input and immutable policy evidence."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, cast

from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
from procurement_intelligence_lab.platform.execution.identity import aware, digest, same, text
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def admit(condition: bool) -> None:
    if not condition:
        raise PackageExecutionError("resolution input requires exact bounded immutable evidence")


@dataclass(frozen=True)
class CandidateSnapshot:
    schema_version: str
    catalog_id: str
    catalog_revision: str
    scope: StateScope
    entity_type: str
    identifier_namespace: str
    effective_at: datetime
    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        admit(self.schema_version == "1.0" and type(self.schema_version) is str)
        for value in (
            self.catalog_id,
            self.catalog_revision,
            self.entity_type,
            self.identifier_namespace,
        ):
            text(value)
        admit(type(self.scope) is StateScope)
        for value in vars(self.scope).values():
            text(value)
        aware(self.effective_at)
        admit(type(self.keys) is tuple and len(self.keys) <= 256)
        for key in self.keys:
            admit(type(key) is str and bool(key.strip()) and len(key) <= 256)
            try:
                key.encode("utf-8")
            except UnicodeError:
                admit(False)
        admit(self.keys == tuple(sorted(set(self.keys))))

    @property
    def content_digest(self) -> str:
        return digest(self)

    @property
    def snapshot_id(self) -> str:
        return "candidate-snapshot-v1:" + self.content_digest


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in items:
        admit(key not in out)
        out[key] = value
    return out


def _constant(value: str) -> None:
    admit(False)


def _snapshot(data: bytes) -> CandidateSnapshot:
    admit(type(data) is bytes and len(data) <= 32768)
    try:
        raw: object = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
        admit(type(raw) is dict)
        value = cast(dict[str, Any], raw)
        admit(
            set(value)
            == {
                "schema_version",
                "catalog_id",
                "catalog_revision",
                "scope",
                "entity_type",
                "identifier_namespace",
                "effective_at",
                "keys",
            }
        )
        scope_raw: object = value["scope"]
        admit(type(scope_raw) is dict)
        scope = cast(dict[str, Any], scope_raw)
        admit(set(scope) == {"tenant_id", "project_id", "site_id", "version"})
        keys_raw: object = value["keys"]
        admit(type(keys_raw) is list)
        keys = cast(list[object], keys_raw)
        admit(all(type(key) is str for key in keys))
        admit(type(value["effective_at"]) is str)
        return CandidateSnapshot(
            value["schema_version"],
            value["catalog_id"],
            value["catalog_revision"],
            StateScope(scope["tenant_id"], scope["project_id"], scope["site_id"], scope["version"]),
            value["entity_type"],
            value["identifier_namespace"],
            datetime.fromisoformat(value["effective_at"]),
            tuple(sorted(cast(list[str], keys))),
        )
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, AttributeError):
        raise PackageExecutionError(
            "candidate input requires bounded unambiguous UTF-8 JSON"
        ) from None


@dataclass(frozen=True)
class CandidateInputEvidence:
    snapshot: CandidateSnapshot
    raw_json: bytes

    def __post_init__(self) -> None:
        admit(type(self.snapshot) is CandidateSnapshot)
        admit(same(_snapshot(self.raw_json), self.snapshot))

    @property
    def raw_sha256(self) -> str:
        return sha256(self.raw_json).hexdigest()


def load_candidate_input(data: bytes) -> CandidateInputEvidence:
    return CandidateInputEvidence(_snapshot(data), data)


@dataclass(frozen=True)
class ResolutionPolicyEvidence:
    reference: ResolvedReference
    entity_type: str
    identifier_namespace: str
    parameters: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        admit(type(self.reference) is ResolvedReference and type(self.parameters) is tuple)
        for pair in self.parameters:
            admit(type(pair) is tuple and len(pair) == 2)
            for value in pair:
                text(value)
        admit(self.parameters == tuple(sorted(self.parameters)))
        values = dict(self.parameters)
        admit(len(values) == len(self.parameters))
        text(self.entity_type)
        text(self.identifier_namespace)
        admit(values.get("entity_type") == self.entity_type)
        admit(values.get("identifier_namespace") == self.identifier_namespace)
        admit(self.reference.content_digest == digest(values))
