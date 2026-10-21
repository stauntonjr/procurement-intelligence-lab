"""Declared execution-instance dependencies; impact is not governing truth or recomputation."""

import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256

from procurement_intelligence_lab.platform.semantics.errors import DependencyContractError
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

POLICY = "declared-dependencies/v1"
DATA = (ProvenanceRelation.USED_INPUT, ProvenanceRelation.DERIVED_FROM)
METADATA = (ProvenanceRelation.USED_SCHEMA, ProvenanceRelation.USED_MODEL)


def text(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 500:
        raise DependencyContractError("dependency text must be nonempty and at most500 characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise DependencyContractError(
            "dependency text must contain valid Unicode scalars"
        ) from None


def aware(value: datetime) -> None:
    if type(value) is not datetime or not isinstance(value.tzinfo, timezone):
        raise DependencyContractError("dependency time must be aware with a fixed offset")


def _strings(values: tuple[str, ...], *, allow_empty: bool = False) -> None:
    if type(values) is not tuple or (not allow_empty and not values):
        raise DependencyContractError("dependency identities require an immutable tuple")
    for value in values:
        text(value)
    if len(values) != len(set(values)):
        raise DependencyContractError("dependency identities must be unique")


def _content(value: "TransformationEvent | DependencySnapshot") -> str:
    return json.dumps(
        asdict(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: item.isoformat(),
    )


@dataclass(frozen=True)
class ArchivedClaimRef:
    snapshot_id: str
    assertion_id: str

    def __post_init__(self) -> None:
        text(self.snapshot_id)
        text(self.assertion_id)


@dataclass(frozen=True)
class ClaimDependency:
    reference_id: str
    event: TransformationEvent

    def __post_init__(self) -> None:
        text(self.reference_id)
        e = self.event
        if type(e) is not TransformationEvent or type(e.provenance) is not DecisionProvenance:
            raise DependencyContractError("dependency requires a typed producer event")
        p, c = e.provenance, e.provenance.context
        if type(c) is not ProvenanceContext or type(p.component_kind) is not ComponentKind:
            raise DependencyContractError("producer requires typed execution provenance")
        for value in (
            e.event_type,
            p.component_name,
            p.implementation_version,
            c.run_id,
            c.workflow_name,
            c.workflow_version,
            c.code_revision,
            c.image_digest,
            c.config_digest,
        ):
            text(value)
        for value in (
            p.policy_version,
            p.model_provider,
            p.model_id,
            p.model_revision,
            p.prompt_version,
            p.schema_version,
            c.parent_run_id,
            c.dependency_lock_digest,
        ):
            if value is not None:
                text(value)
        aware(c.started_at)
        if c.environment != ():
            raise DependencyContractError("raw producer environment entries are unsupported")
        _strings(c.input_snapshot_ids)
        _strings(e.output_ids)
        _strings(e.parent_event_ids, allow_empty=True)
        if self.reference_id not in e.output_ids or type(e.input_edges) is not tuple:
            raise DependencyContractError("reference must be an explicit producer output")
        for edge in e.input_edges:
            if type(edge) is not ProvenanceEdge or type(edge.relation) is not ProvenanceRelation:
                raise DependencyContractError("dependency requires typed input edges")
            text(edge.target_id)
            if edge.relation not in (*DATA, *METADATA):
                raise DependencyContractError("unsupported producer relationship")
        if not self.inputs or len(self.inputs) > 32 or len(set(self.inputs)) != len(self.inputs):
            raise DependencyContractError("producer requires1..32 unique data inputs")

    @property
    def inputs(self) -> tuple[str, ...]:
        return tuple(e.target_id for e in self.event.input_edges if e.relation in DATA)


@dataclass(frozen=True)
class DependencyImpact:
    affected: tuple[tuple[str, int], ...]
    links: tuple[tuple[str, str], ...]
    frontier: tuple[str, ...]

    @property
    def traversal_complete(self) -> bool:
        return not self.frontier

    @property
    def coverage(self) -> str:
        return "registered_graph_only"

    @property
    def global_completeness(self) -> str:
        return "not_evaluated"


@dataclass(frozen=True)
class DependencyManifest:
    scope: StateScope
    request_id: str
    roots: tuple[ArchivedClaimRef, ...]
    claims: tuple[ClaimDependency, ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not StateScope:
            raise DependencyContractError("dependency requires exact state scope")
        for value in (
            self.request_id,
            self.scope.tenant_id,
            self.scope.project_id,
            self.scope.site_id,
            self.scope.version,
        ):
            text(value)
        if (
            type(self.roots) is not tuple
            or not 1 <= len(self.roots) <= 128
            or any(type(r) is not ArchivedClaimRef for r in self.roots)
            or type(self.claims) is not tuple
            or len(self.claims) > 256
            or any(type(c) is not ClaimDependency for c in self.claims)
        ):
            raise DependencyContractError("dependency manifest requires bounded typed roots/claims")
        roots = tuple(r.assertion_id for r in self.roots)
        refs = tuple(c.reference_id for c in self.claims)
        if (
            roots != tuple(sorted(set(roots)))
            or refs != tuple(sorted(set(refs)))
            or set(roots) & set(refs)
        ):
            raise DependencyContractError(
                "root/output identities must be unique and canonically ordered"
            )
        known = set(roots) | set(refs)
        snapshots = {r.snapshot_id for r in self.roots}
        if any(
            set(c.inputs) - known or set(c.event.provenance.context.input_snapshot_ids) - snapshots
            for c in self.claims
        ):
            raise DependencyContractError(
                "producer inputs must belong to the declared graph/snapshots"
            )
        producers = {c.reference_id: c.event for c in self.claims}
        for claim in self.claims:
            for output in claim.event.output_ids:
                if output in roots or (
                    output in producers and _content(producers[output]) != _content(claim.event)
                ):
                    raise DependencyContractError(
                        "registered output has conflicting producer receipts"
                    )
        reached = set(roots)
        pending = list(self.claims)
        while pending:
            ready = [c for c in pending if set(c.inputs) <= reached]
            if not ready:
                raise DependencyContractError("dependency graph must be acyclic")
            reached.update(c.reference_id for c in ready)
            pending = [c for c in pending if c not in ready]

    def impact(self, source_id: str, max_depth: int) -> DependencyImpact:
        if type(max_depth) is not int or not 1 <= max_depth <= 32:
            raise DependencyContractError("impact depth must be an integer from1 through32")
        if source_id not in {r.assertion_id for r in self.roots}:
            raise DependencyContractError("impact source must be a declared root")
        edges = {(i, c.reference_id) for c in self.claims for i in c.inputs}
        downstream: dict[str, list[str]] = {}
        for source, target in sorted(edges):
            downstream.setdefault(source, []).append(target)
        depths = {source_id: 0}
        queue = deque([source_id])
        while queue:
            source = queue.popleft()
            if depths[source] == max_depth:
                continue
            for target in downstream.get(source, []):
                if target not in depths:
                    depths[target] = depths[source] + 1
                    queue.append(target)
        frontier = tuple(
            sorted(
                {
                    target
                    for source in depths
                    for target in downstream.get(source, [])
                    if target not in depths
                }
            )
        )
        return DependencyImpact(
            tuple(sorted((r, d) for r, d in depths.items() if d)),
            tuple(sorted((s, t) for s, t in edges if s in depths and t in depths)),
            frontier,
        )


@dataclass(frozen=True)
class DependencySnapshot:
    manifest: DependencyManifest
    recorder_id: str
    recorded_at: datetime
    policy_reference: str = POLICY

    def __post_init__(self) -> None:
        if type(self.manifest) is not DependencyManifest or self.policy_reference != POLICY:
            raise DependencyContractError("dependency snapshot requires its typed manifest/policy")
        text(self.recorder_id)
        aware(self.recorded_at)
        if any(
            c.event.provenance.context.started_at > self.recorded_at for c in self.manifest.claims
        ):
            raise DependencyContractError("producer execution cannot be recorded in the future")

    @property
    def snapshot_id(self) -> str:
        return stable_id("dependency-snapshot-v1", self.manifest.scope, self.manifest.request_id)

    @property
    def digest(self) -> str:
        payload = _content(self)
        return sha256(payload.encode()).hexdigest()
