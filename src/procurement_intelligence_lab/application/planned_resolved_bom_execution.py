"""Separate opt-in six-stage application result and explicit preparation."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from procurement_intelligence_lab.application.planned_bom_execution import (
    PlannedBomExecution,
    PlannedBomExecutionService,
)
from procurement_intelligence_lab.platform.execution.contracts import plan_payload
from procurement_intelligence_lab.platform.execution.identity import encoded
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
    ResolveExecutorRegistration,
)
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
    ResolvedPrefixExecutionReceipt,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.execution.resolution_runner import (
    ResolvedPrefixExecution,
    run_resolved_prefix,
)
from procurement_intelligence_lab.platform.execution.runner import PrefixExecution


def resolved_execution_receipt_payload(r: ResolvedPrefixExecutionReceipt) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "profile": "resolved-prefix-execution/v1",
        "stop_after": "RESOLVE",
        "requested_prefix_complete": True,
        "package_execution_complete": False,
        "execution_digest": r.execution_digest,
        "receipt_digest": r.receipt_digest,
        "plan_hash": r.plan.plan_hash,
        "plan": plan_payload(r.plan),
        "context": encoded(r.context),
        "candidate_snapshot_id": r.candidate_input.snapshot.snapshot_id,
        "candidate_raw_sha256": r.candidate_input.raw_sha256,
        "policy": encoded(r.policy),
        "entries": encoded(r.entries),
        "completed_at": r.completed_at.isoformat(),
        "execution_context_basis": "caller_pinned_local_catalog",
        "durable_run_journal_updated": False,
        "result_cache_updated": False,
    }


@dataclass(frozen=True)
class PlannedResolvedBomExecution:
    execution: ResolvedPrefixExecution

    def as_dict(self) -> dict[str, Any]:
        r = self.execution.receipt
        base = PlannedBomExecution(PrefixExecution(r.prefix.output, r.prefix)).as_dict()
        o = self.execution.output
        outcomes = [
            {
                "outcome_id": x.outcome_id,
                "mention_id": x.mention.mention_id,
                "decision_id": x.decision.decision_id,
                "status": x.decision.status.value,
                "canonical_key": x.decision.canonical_key,
                "matched_keys": list(x.matched_keys),
                "rationale": x.decision.rationale,
                "evidence": encoded(x.decision.evidence),
                "provenance": encoded(x.decision.provenance),
            }
            for x in o.outcomes
        ]
        return {
            **base,
            "executed_stages": ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT", "RESOLVE"],
            "transformations": [
                *cast(list[dict[str, Any]], base["transformations"]),
                {"event_id": o.event.event_id, **cast(dict[str, Any], encoded(o.event))},
            ],
            "prefix_execution_receipt": base["execution_receipt"],
            "execution_receipt": resolved_execution_receipt_payload(r),
            "resolution": {
                "batch_id": o.batch_id,
                "candidates": encoded(o.candidates),
                "candidate_snapshot_id": o.candidates.snapshot_id,
                "candidate_raw_sha256": r.candidate_input.raw_sha256,
                "candidate_raw_json_hex": r.candidate_input.raw_json.hex(),
                "policy": encoded(o.policy),
                "outcomes": outcomes,
                "canonicalized_assertions": [
                    {
                        "canonicalized_assertion_id": c.canonicalized_assertion_id,
                        **cast(dict[str, Any], encoded(c)),
                    }
                    for c in o.canonicalized
                ],
                "unlinked_assertion_ids": list(o.unlinked_assertion_ids),
            },
        }


@dataclass(frozen=True)
class PlannedResolvedBomExecutionService:
    prefix: PlannedBomExecutionService
    resolution: ResolveExecutorRegistration
    validate_inputs: Callable[[ResolvedExecutionRequest], None]
    clock: Callable[[], datetime]

    def prepare(self, request: ResolvedExecutionRequest) -> PreparedResolvedPrefix:
        admit(type(request) is ResolvedExecutionRequest)
        self.validate_inputs(request)
        return PreparedResolvedPrefix(self.prefix.prepare(request.prefix), request, self.resolution)

    def execute(self, request: ResolvedExecutionRequest) -> PlannedResolvedBomExecution:
        return PlannedResolvedBomExecution(
            run_resolved_prefix(self.prepare(request), clock=self.clock)
        )
