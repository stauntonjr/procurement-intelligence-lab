"""Application orchestration for the evidence-first BOM vertical slice."""

from dataclasses import dataclass

from procurement_intelligence_lab.domain.assertions import (
    SourceAssertion,
    assertions_for_bom,
)
from procurement_intelligence_lab.domain.bom import Bom
from procurement_intelligence_lab.domain.evidence import EvidenceChain, pipeline_chain
from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    local_provenance_context,
)
from procurement_intelligence_lab.domain.reconciliation import (
    ReconciledLine,
    ReconciliationPolicy,
    ReconciliationPolicyError,
    reconcile_lines,
)
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    resolve_identifier,
)
from procurement_intelligence_lab.domain.scope import Permission, RequestContext
from procurement_intelligence_lab.domain.state import OperationalBomLine, project_operational_lines


@dataclass(frozen=True)
class BomPipelineResult:
    assertions: tuple[SourceAssertion, ...]
    decisions: tuple[ResolutionDecision, ...]
    operational_lines: tuple[OperationalBomLine, ...]
    reconciled_lines: tuple[ReconciledLine, ...]
    evidence: EvidenceChain
    provenance: ProvenanceContext


def run_bom_pipeline(
    bom: Bom,
    canonical_candidates: tuple[str, ...],
    *,
    provenance: ProvenanceContext | None = None,
    request_context: RequestContext | None = None,
    reconciliation_policy: ReconciliationPolicy | None = None,
) -> BomPipelineResult:
    if request_context is not None:
        request_context.require(Permission.READ_STATE)
    context = provenance or local_provenance_context()
    resolution_provenance = DecisionProvenance(
        context,
        "normalized-exact-resolver",
        ComponentKind.DETERMINISTIC,
        "1",
    )
    reconciliation_provenance = DecisionProvenance(
        context,
        "deterministic-reconciliation",
        ComponentKind.DETERMINISTIC,
        "1",
    )
    assertions = assertions_for_bom(bom)
    decisions = tuple(
        resolve_identifier(
            line.sku,
            canonical_candidates,
            assertions,
            provenance=resolution_provenance,
        )
        for line in bom.lines
    )
    operational_lines = project_operational_lines(bom, decisions)
    sources = tuple(sorted({line.source_artifact for line in operational_lines}))
    if reconciliation_policy is None:
        if len(sources) > 1:
            raise ReconciliationPolicyError(
                "multiple source artifacts require an explicit reconciliation policy"
            )
        reconciliation_policy = ReconciliationPolicy(sources or (bom.artifact_id,))
    reconciled_lines = reconcile_lines(
        operational_lines,
        policy=reconciliation_policy,
        provenance=reconciliation_provenance,
    )
    evidence_refs = tuple(line.evidence for line in bom.lines)
    if not reconciled_lines:
        reconciliation_status = "unresolved"
    elif any(line.status == "conflict" for line in reconciled_lines):
        reconciliation_status = "conflict"
    else:
        reconciliation_status = "reconciled"
    return BomPipelineResult(
        assertions,
        decisions,
        operational_lines,
        reconciled_lines,
        pipeline_chain(
            "BOM operational state",
            evidence_refs,
            decisions,
            operational_lines,
            reconciliation_status,
        ),
        context,
    )
