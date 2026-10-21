"""Execute a real source query and retain its actual producer dependency receipt."""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from procurement_intelligence_lab.application.archived_documents import ArchiveReader, snapshot_for
from procurement_intelligence_lab.application.correction_impact import snapshot_payload
from procurement_intelligence_lab.application.document_reviews import authorize
from procurement_intelligence_lab.domains.procurement.source_queries import (
    SourceSkuQuery,
    execution_digest,
    query_provenance,
    validate_execution,
)
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ArchivedClaimRef,
    ClaimDependency,
    DependencyManifest,
    DependencySnapshot,
    aware,
    text,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyContractError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceContext,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.ports.dependencies import DependencyStore


def dependency_manifest(query: SourceSkuQuery, request_id: str) -> DependencyManifest:
    return DependencyManifest(
        query.snapshot.artifact.source.scope,
        request_id,
        tuple(
            ArchivedClaimRef(query.snapshot.snapshot_id, a.assertion_id)
            for a in sorted(query.inputs, key=lambda a: a.assertion_id)
        ),
        (ClaimDependency(query.reference_id, query.event),),
    )


@dataclass(frozen=True)
class SourceQueryExecution:
    query: SourceSkuQuery
    registration: DependencySnapshot

    def __post_init__(self) -> None:
        if (
            type(self.query) is not SourceSkuQuery
            or type(self.registration) is not DependencySnapshot
            or self.registration.manifest
            != dependency_manifest(self.query, self.registration.manifest.request_id)
        ):
            raise SourceQueryContractError(
                "query result must retain its exact producer dependency manifest"
            )

    def as_dict(self) -> dict[str, Any]:
        query = self.query
        snapshot = query.snapshot
        provenance = asdict(query.provenance)
        provenance["context"]["started_at"] = query.provenance.context.started_at.isoformat()
        return {
            "query": {
                "kind": "distinct_source_skus",
                "reference_id": query.reference_id,
                "value": query.value,
                "known_source_skus": query.known_skus,
                "status": query.status.value,
                "missing_assertion_ids": query.missing_assertion_ids,
                "source_snapshot_id": snapshot.snapshot_id,
                "source_scope": asdict(snapshot.artifact.source.scope),
                "source_observed_at": snapshot.artifact.source.observed_at.isoformat(),
                "source_captured_at": snapshot.artifact.captured_at.isoformat(),
                "execution_digest": query.execution_digest,
                "provenance": provenance,
                "producer_event": {
                    "event_id": query.event.event_id,
                    "event_type": query.event.event_type,
                    "input_edges": [
                        {"relation": e.relation.value, "target_id": e.target_id}
                        for e in query.event.input_edges
                    ],
                    "output_ids": query.event.output_ids,
                    "parent_event_ids": query.event.parent_event_ids,
                },
                "inputs": [
                    {
                        "assertion_id": a.assertion_id,
                        "value": a.value,
                        "evidence": a.evidence.as_dict(),
                    }
                    for a in query.inputs
                ],
                "canonical_identity_established": False,
                "governing_state_updated": False,
                "corrections_applied": False,
            },
            "dependency_snapshot": snapshot_payload(self.registration),
            "producer_execution": "synchronous_local_query",
            "execution_context_basis": "caller_pinned_local_manifest",
            "query_result_materialized": False,
            "retention": "dependency_receipt_only",
        }


@dataclass(frozen=True)
class ArchivedBomQueryService:
    reader: ArchiveReader
    dependencies: DependencyStore
    producer: Callable[[DocumentSnapshot, DecisionProvenance], SourceSkuQuery]
    clock: Callable[[], datetime]

    def execute(
        self,
        scope: StateScope,
        snapshot_id: str,
        request_id: str,
        execution: ProvenanceContext,
        *,
        context: RequestContext,
    ) -> SourceQueryExecution:
        authorize(context, scope, Permission.REVIEW)
        authorize(context, scope, Permission.READ_EVIDENCE)
        try:
            for value in (
                snapshot_id,
                request_id,
                context.principal_id,
                scope.tenant_id,
                scope.project_id,
                scope.site_id,
                scope.version,
            ):
                text(value)
            recorded_at = self.clock()
            aware(recorded_at)
        except DependencyContractError:
            raise SourceQueryContractError(
                "source query identities or server recording clock are invalid"
            ) from None
        validate_execution(execution, snapshot_id)
        if execution.started_at > recorded_at:
            raise SourceQueryContractError(
                "source query execution cannot be recorded in the future"
            )
        source = self.reader.show(scope, snapshot_id)
        snapshot = snapshot_for(source.result, source.policy_parameters)
        expected_provenance = query_provenance(execution)
        query = self.producer(snapshot, expected_provenance)
        if (
            type(query) is not SourceSkuQuery
            or query.snapshot is not snapshot
            or query.execution_digest != execution_digest(expected_provenance)
        ):
            raise SourceQueryContractError(
                "source query producer must retain the exact requested snapshot"
            )
        # Stamp registration after actual computation, independently of the preflight clock check.
        try:
            recorded_at = self.clock()
            aware(recorded_at)
        except DependencyContractError:
            raise SourceQueryContractError("source query registration clock is invalid") from None
        if recorded_at < execution.started_at:
            raise SourceQueryContractError("source query registration cannot precede execution")
        registration = self.dependencies.append(
            dependency_manifest(query, request_id), context.principal_id, recorded_at
        )
        return SourceQueryExecution(query, registration)
