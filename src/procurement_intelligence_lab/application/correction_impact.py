"""Authorized, read-only impact over exact immutable producer declarations and human decisions."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from procurement_intelligence_lab.application.document_review_payloads import history_payload
from procurement_intelligence_lab.application.document_reviews import (
    DocumentReviewService,
    authorize,
)
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ArchivedClaimRef,
    DependencyManifest,
    DependencySnapshot,
    aware,
    text,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import ReviewOutcome
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyConflictError,
    DependencyNotFoundError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)
from procurement_intelligence_lab.ports.dependencies import DependencyStore


def snapshot_payload(snapshot: DependencySnapshot) -> dict[str, Any]:
    return {
        "dependency_snapshot_id": snapshot.snapshot_id,
        "digest": snapshot.digest,
        "scope": {
            "tenant_id": snapshot.manifest.scope.tenant_id,
            "project_id": snapshot.manifest.scope.project_id,
            "site_id": snapshot.manifest.scope.site_id,
            "version": snapshot.manifest.scope.version,
        },
        "recorder_id": snapshot.recorder_id,
        "recorded_at": snapshot.recorded_at.isoformat(),
        "policy": snapshot.policy_reference,
        "coverage": "registered_graph_only",
        "global_completeness": "not_evaluated",
        "basis": "caller_declared_producer_receipts",
    }


@dataclass(frozen=True)
class CorrectionImpactService:
    dependencies: DependencyStore
    reviews: DocumentReviewService
    clock: Callable[[], datetime]

    def register(
        self, manifest: DependencyManifest, *, context: RequestContext
    ) -> DependencySnapshot:
        authorize(context, manifest.scope, Permission.REVIEW)
        authorize(context, manifest.scope, Permission.READ_EVIDENCE)
        return self.dependencies.append(manifest, context.principal_id, self.clock())

    def inspect(
        self,
        scope: StateScope,
        snapshot_id: str,
        task_id: str,
        *,
        as_of: datetime,
        max_depth: int,
        context: RequestContext,
    ) -> dict[str, Any]:
        authorize(context, scope, Permission.READ_EVIDENCE)
        aware(as_of)
        text(snapshot_id)
        text(task_id)
        snapshot = self.dependencies.get(scope, snapshot_id)
        if snapshot.recorded_at > as_of:
            raise DependencyNotFoundError("dependency snapshot was not recorded at requested as-of")
        review = self.reviews.show(scope, task_id, context=context, as_of=as_of)
        if review.decision is None or review.decision.command.outcome is not ReviewOutcome.APPROVE:
            raise DependencyConflictError("impact requires an approved correction visible at as-of")
        source = review.task.proposal
        if (
            ArchivedClaimRef(source.snapshot_id, source.previous.assertion_id)
            not in snapshot.manifest.roots
        ):
            raise DependencyNotFoundError("review source is not an exact dependency snapshot root")
        impact = snapshot.manifest.impact(source.previous.assertion_id, max_depth)
        producers = {c.reference_id: c for c in snapshot.manifest.claims}
        return {
            "dependency_snapshot": snapshot_payload(snapshot),
            "review": history_payload(review),
            "as_of": as_of.isoformat(),
            "max_depth": max_depth,
            "affected": [
                {
                    "reference_id": ref,
                    "minimum_depth": depth,
                    "potentially_stale": True,
                    "producer_event_id": producers[ref].event.event_id,
                    "producer_provenance_id": producers[ref].event.provenance.provenance_id,
                    "recomputation_required": True,
                }
                for ref, depth in impact.affected
            ],
            "links": [{"input_id": a, "output_id": b} for a, b in impact.links],
            "frontier": list(impact.frontier),
            "traversal_complete": impact.traversal_complete,
            "coverage": impact.coverage,
            "global_completeness": impact.global_completeness,
            "recomputation_executed": False,
            "governing_state_updated": False,
        }
