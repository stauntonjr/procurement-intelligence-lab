"""Authorized explicit replay of selected approved source-value corrections."""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from procurement_intelligence_lab.application.archived_documents import ArchiveReader, snapshot_for
from procurement_intelligence_lab.application.correction_impact import snapshot_payload
from procurement_intelligence_lab.application.document_review_payloads import history_payload
from procurement_intelligence_lab.application.document_reviews import (
    DocumentReviewService,
    authorize,
)
from procurement_intelligence_lab.application.document_stages import provenance_payload
from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
    QUERY_COMPONENT,
    ReviewedSourceSkuQuery,
    reviewed_dependency_manifest,
    reviewed_query_provenance,
    validate_provenance,
)
from procurement_intelligence_lab.domains.procurement.source_queries import (
    execution_digest,
    validated_sku_inputs,
)
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.dependencies import (
    DependencySnapshot,
    aware,
    text,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewHistory
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyContractError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceContext,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.ports.dependencies import DependencyStore


def event_payload(event: TransformationEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "input_edges": [
            {"relation": e.relation.value, "target_id": e.target_id} for e in event.input_edges
        ],
        "output_ids": event.output_ids,
        "parent_event_ids": event.parent_event_ids,
        "provenance": provenance_payload(event.provenance),
    }


@dataclass(frozen=True)
class ReviewedQueryExecution:
    query: ReviewedSourceSkuQuery
    registration: DependencySnapshot

    def __post_init__(self) -> None:
        if (
            type(self.query) is not ReviewedSourceSkuQuery
            or type(self.registration) is not DependencySnapshot
            or self.registration.manifest.digest
            != reviewed_dependency_manifest(
                self.query, self.registration.manifest.request_id
            ).digest
        ):
            raise SourceQueryContractError(
                "reviewed execution must retain its exact dependency manifest"
            )

    def as_dict(self) -> dict[str, Any]:
        q = self.query
        return {
            "reviewed_query": {
                "kind": "selected_reviewed_source_skus",
                "reference_id": q.reference_id,
                "value": q.value,
                "known_source_skus": q.known_skus,
                "status": q.status.value,
                "missing_reference_ids": q.missing_reference_ids,
                "as_of": q.as_of.isoformat(),
                "source_snapshot_id": q.snapshot.snapshot_id,
                "source_scope": asdict(q.snapshot.artifact.source.scope),
                "execution_digest": q.execution_digest,
                "producer_event": event_payload(q.event),
                "inputs": [{"reference_id": ref, "value": value} for ref, value in q.inputs],
                "source_inputs": [
                    {
                        "assertion_id": a.assertion_id,
                        "original_value": a.value,
                        "evidence": a.evidence.as_dict(),
                    }
                    for a in validated_sku_inputs(q.snapshot)
                ],
                "reviewed_rows": [
                    {
                        "reference_id": r.reference_id,
                        "source_assertion_id": r.source.assertion_id,
                        "value": r.value,
                        "review_task_id": r.review.task.task_id,
                        "review_digest": r.review.digest,
                        "producer_event": event_payload(r.event),
                    }
                    for r in q.rows
                ],
            },
            "selected_reviews": [history_payload(r) for r in q.reviews],
            "dependency_snapshot": snapshot_payload(self.registration),
            "correction_selection": "explicit_selected_set",
            "unselected_reviews": "not_evaluated",
            "coverage": "registered_graph_only",
            "global_completeness": "not_evaluated",
            "recomputation_executed": True,
            "original_source_updated": False,
            "governing_state_updated": False,
            "canonical_identity_established": False,
            "query_result_materialized": False,
            "producer_execution": "synchronous_local_reviewed_query",
            "execution_context_basis": "caller_pinned_local_manifest",
        }


type Producer = Callable[
    [DocumentSnapshot, tuple[ReviewHistory, ...], datetime, DecisionProvenance],
    ReviewedSourceSkuQuery,
]


@dataclass(frozen=True)
class ReviewedBomQueryService:
    reader: ArchiveReader
    reviews: DocumentReviewService
    dependencies: DependencyStore
    producer: Producer
    clock: Callable[[], datetime]

    def execute(
        self,
        scope: StateScope,
        snapshot_id: str,
        request_id: str,
        task_ids: tuple[str, ...],
        as_of: datetime,
        execution: ProvenanceContext,
        *,
        context: RequestContext,
    ) -> ReviewedQueryExecution:
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
            if type(task_ids) is not tuple or not 1 <= len(task_ids) <= 32:
                raise SourceQueryContractError(
                    "reviewed task selection requires1..32 immutable IDs"
                )
            for value in task_ids:
                text(value)
            if len(set(task_ids)) != len(task_ids):
                raise SourceQueryContractError("reviewed task IDs must be unique")
            before = self.clock()
            aware(before)
        except DependencyContractError:
            raise SourceQueryContractError(
                "reviewed identities/selection/server clock are invalid"
            ) from None
        provenance = reviewed_query_provenance(execution)
        validate_provenance(provenance, snapshot_id, QUERY_COMPONENT, as_of)
        if execution.started_at > before:
            raise SourceQueryContractError(
                "reviewed execution cannot be future relative to server clock"
            )
        source = self.reader.show(scope, snapshot_id)
        snapshot = snapshot_for(source.result, source.policy_parameters)
        if snapshot.snapshot_id != snapshot_id:
            raise SourceQueryContractError("reviewed reader must retain exact requested source")
        selected = tuple(
            sorted(
                (
                    self.reviews.show(scope, t, context=context, as_of=as_of)
                    for t in sorted(task_ids)
                ),
                key=lambda r: r.task.task_id,
            )
        )
        query = self.producer(snapshot, selected, as_of, provenance)
        if (
            type(query) is not ReviewedSourceSkuQuery
            or query.snapshot is not snapshot
            or tuple(r.digest for r in query.reviews) != tuple(r.digest for r in selected)
            or query.as_of.isoformat() != as_of.isoformat()
            or query.execution_digest != execution_digest(provenance)
        ):
            raise SourceQueryContractError(
                "reviewed producer must retain exact requested source/selection/as-of/context"
            )
        try:
            recorded_at = self.clock()
            aware(recorded_at)
        except DependencyContractError:
            raise SourceQueryContractError("reviewed registration clock is invalid") from None
        if recorded_at < execution.started_at:
            raise SourceQueryContractError("reviewed registration cannot precede execution")
        manifest = reviewed_dependency_manifest(query, request_id)
        receipt = self.dependencies.append(manifest, context.principal_id, recorded_at)
        if (
            type(receipt) is not DependencySnapshot
            or receipt.manifest.digest != manifest.digest
            or receipt.recorder_id != context.principal_id
            or receipt.recorded_at > recorded_at
        ):
            raise SourceQueryContractError(
                "reviewed registration must retain command, recorder and server time"
            )
        return ReviewedQueryExecution(query, receipt)
