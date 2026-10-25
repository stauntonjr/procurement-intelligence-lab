"""Synthetic actual six-stage producers; simulated archive receipts only in unit tests."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    ExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionStatus,
    ResolvedReference,
    StageExecutionEntry,
)
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
    CompletedResolvedPrefixSnapshot,
    ResolvedExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, SCOPE, provenance
from tests.contract.test_bom_assertions import POLICY
from tests.planned_execution_archive_fixtures import parameters
from tests.planning_fixtures import planning_inputs
from tests.resolved_execution_fixtures import planned_resolved_inputs


def producer(
    tmp_path: Path,
    rows: str = HEADER + ROW,
    keys: tuple[str, ...] = ("GPU-A",),
    content: bytes | None = None,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    m, r, c, q, path = planned_resolved_inputs(tmp_path, rows=rows, keys=keys)
    if content is not None:
        path.write_bytes(content)
    service = bootstrap.build_planned_resolved_bom_service(
        manifest=m,
        registry=r,
        config=c,
        normalization_policy=POLICY,
        resolution_policy=BomResolutionPolicy.from_parameters(q.policy.parameters),
        candidate_input=q.candidate_input,
        clock=lambda: AT + timedelta(seconds=1),
    )
    completed = CompletedResolvedPrefixSnapshot.from_execution(
        service.execute(q).execution.receipt, parameters()
    )
    s = completed.prefix.snapshot
    a = ArchiveReceipt(
        1,
        s.snapshot_id,
        SCOPE,
        s.artifact.artifact_id,
        s.artifact.content_hash,
        len(s.assertions),
        s.origin.recorded_at,
    )
    p = ArchivedPrefix(
        completed.prefix,
        ExecutionArchiveReceipt(
            1, completed.prefix.execution_digest, completed.prefix.execution.receipt_digest, a
        ),
    )
    return ArchivedResolvedPrefix(
        completed,
        ResolvedExecutionArchiveReceipt(
            1, completed.execution_digest, completed.execution.receipt_digest, p.receipt
        ),
        p,
    ), path.read_bytes()


def metadata(producers: tuple[ArchivedResolvedPrefix, ...], **changes: Any) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for i, p in enumerate(producers):
        a = p.completed.prefix.snapshot.artifact
        records.append(
            {
                "execution_digest": p.completed.execution_digest,
                "artifact_id": a.artifact_id,
                "content_hash": a.content_hash,
                "revision_id": f"revision-{i}",
                "supersedes_revision_ids": [],
                "source_role": "approved_bom_revision",
                "approval": {
                    "record_ref": f"synthetic-approval-{i}",
                    "approved_at": AT.isoformat(),
                },
                "effective_from": AT.isoformat(),
                "effective_until": None,
                "document_at": AT.isoformat(),
            }
        )
    if changes:
        records[0].update(changes)
    return {"schema_version": "1.0", "producers": records}


def policy():
    from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
        ReconciliationPolicyEvidence,
    )

    params = tuple(
        sorted(
            {
                "profile": "retained-resolution-reconciliation/v1",
                "policy_id": "procurement-governing-claims/v1",
                "predicate": "required_quantity",
                "quantity_unit": "each",
            }.items()
        )
    )
    return ReconciliationPolicyEvidence(
        ResolvedReference(
            "procurement.reconcile/governed-required-quantity@1",
            "procurement-governing-claims/v1",
            digest(dict(params)),
        ),
        params,
    )


def operation_inputs(
    producers: tuple[ArchivedResolvedPrefix, ...], authority: dict[str, Any] | None = None
):
    from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
        OperationAuthorityEvidence,
        RetainedReconciliationInputs,
    )

    wire = metadata(producers) if authority is None else authority
    raw = json.dumps(wire).encode()
    semantic = json.dumps(
        {
            "schema_version": "1.0",
            "producers": sorted(wire["producers"], key=lambda r: r["execution_digest"]),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return RetainedReconciliationInputs(
        SCOPE,
        AT,
        tuple(sorted(producers, key=lambda p: p.completed.execution_digest)),
        OperationAuthorityEvidence("procurement-source-authority/v1", raw, semantic),
        policy(),
    )


def operation_plan():
    data = json.loads(bootstrap.compile_procurement_manifest().canonical_json)
    data["source_profile"]["id"] = "retained-resolved-required-quantity"
    data["stages"][6]["policy_refs"] = [policy().reference.declaration_ref]
    m = json.dumps(data).encode()
    r, c = planning_inputs(m)
    return plan_manifest(m, registry=r, config=c)


def empty_receipt(tmp_path: Path):
    from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
        ReconciliationOperationReceipt,
    )
    from procurement_intelligence_lab.platform.execution.reconciliation_outputs import (
        ReconciledOutput,
    )

    p, _ = producer(tmp_path, HEADER)
    inputs = operation_inputs((p,))
    plan = operation_plan()
    binding = json.loads(plan.canonical_json)["stages"][6]
    context = replace(
        provenance().context, code_revision="test-build", started_at=AT + timedelta(seconds=3)
    )
    dp = DecisionProvenance(
        replace(context, input_snapshot_ids=inputs.input_ids),
        binding["implementation"]["implementation_id"],
        ComponentKind.DETERMINISTIC,
        binding["implementation"]["implementation_version"],
        policy_version=inputs.policy.reference.reference_id,
    )
    output = ReconciledOutput(inputs, (), (), (), b"{}", dp)
    entries = tuple(
        StageExecutionEntry(
            s,
            StageMode(json.loads(plan.canonical_json)["stages"][i]["mode"]),
            ExecutionStatus.SUCCEEDED if s is StageId.RECONCILE else ExecutionStatus.NOT_EXECUTED,
            None if s is StageId.RECONCILE else "outside_requested_prefix",
            dp.component_name if s is StageId.RECONCILE else None,
            inputs.input_ids if s is StageId.RECONCILE else (),
            output.reference_ids if s is StageId.RECONCILE else (),
            output.event.event_id if s is StageId.RECONCILE else None,
        )
        for i, s in enumerate(StageId)
    )
    return ReconciliationOperationReceipt(plan, context, output, entries, AT + timedelta(seconds=4))
