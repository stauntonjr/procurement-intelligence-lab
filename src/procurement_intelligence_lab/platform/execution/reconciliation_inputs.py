"""Neutral immutable evidence for one operation over explicitly retained producers."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
from procurement_intelligence_lab.platform.execution.identity import (
    aware,
    canonical,
    digest,
    same,
    text,
)
from procurement_intelligence_lab.platform.execution.outputs import immutable_output
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.semantics.errors import (
    UnsupportedReconciliationInputError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class OperationAuthorityEvidence:
    schema_id: str
    raw_json: bytes
    semantic_json: bytes

    def __post_init__(self) -> None:
        text(self.schema_id)
        admit(
            all(
                type(v) is bytes and 0 < len(v) <= 65536
                for v in (self.raw_json, self.semantic_json)
            )
        )
        try:
            self.raw_json.decode("utf-8")
            self.semantic_json.decode("utf-8")
        except UnicodeError:
            admit(False)

    @property
    def raw_sha256(self) -> str:
        return sha256(self.raw_json).hexdigest()

    @property
    def semantic_digest(self) -> str:
        return sha256(self.semantic_json).hexdigest()


@dataclass(frozen=True)
class ReconciliationPolicyEvidence:
    reference: ResolvedReference
    parameters: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        admit(type(self.reference) is ResolvedReference and type(self.parameters) is tuple)
        for pair in self.parameters:
            admit(type(pair) is tuple and len(pair) == 2)
            for v in pair:
                text(v)
        admit(
            self.parameters == tuple(sorted(self.parameters))
            and len(dict(self.parameters)) == len(self.parameters)
        )
        admit(self.reference.content_digest == digest(dict(self.parameters)))


@dataclass(frozen=True)
class RetainedReconciliationInputs:
    scope: StateScope
    as_of: datetime
    recorded_producers: tuple[ArchivedResolvedPrefix, ...]
    authority: OperationAuthorityEvidence
    policy: ReconciliationPolicyEvidence

    def __post_init__(self) -> None:
        immutable_output(self)
        admit(
            type(self.scope) is StateScope
            and type(self.authority) is OperationAuthorityEvidence
            and type(self.policy) is ReconciliationPolicyEvidence
        )
        for v in vars(self.scope).values():
            text(v)
        aware(self.as_of)
        ps = self.recorded_producers
        admit(
            type(ps) is tuple
            and 1 <= len(ps) <= 8
            and all(type(p) is ArchivedResolvedPrefix for p in ps)
        )
        keys = tuple(p.completed.execution_digest for p in ps)
        admit(keys == tuple(sorted(set(keys))))
        artifacts = tuple(p.completed.prefix.snapshot.artifact for p in ps)
        if len({a.artifact_id for a in artifacts}) != len(ps) or len(
            {a.content_hash for a in artifacts}
        ) != len(ps):
            raise UnsupportedReconciliationInputError(
                "selected producers repeat source artifact or content"
            )
        admit(all(same(p.completed.scope, self.scope) for p in ps))
        catalog = ps[0].completed.execution.output.candidates
        admit(all(same(p.completed.execution.output.candidates, catalog) for p in ps))

    @property
    def input_ids(self) -> tuple[str, ...]:
        return tuple(
            v
            for p in self.recorded_producers
            for v in (
                p.completed.execution_digest,
                p.completed.execution.output.batch_id,
                p.completed.execution.output.event.event_id,
            )
        ) + (self.authority.semantic_digest, self.policy.reference.reference_id)

    @property
    def semantic_payload(self) -> bytes:
        return canonical(
            (
                self.scope,
                self.as_of,
                tuple(
                    (p.completed.execution.computation_payload, p.completed.prefix.snapshot)
                    for p in self.recorded_producers
                ),
                self.authority.schema_id,
                self.authority.semantic_json,
                self.policy,
            )
        )
