"""Read-only claims and evidence service for inspector and chat adapters."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.application.pipeline import run_bom_pipeline
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine
from procurement_intelligence_lab.domains.procurement.evidence import EvidenceChain, pipeline_chain
from procurement_intelligence_lab.domains.procurement.reconciliation import ReconciledLine
from procurement_intelligence_lab.domains.procurement.state import OperationalBomLine
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext


class ClaimKind(StrEnum):
    DISTINCT_SKUS = "distinct_skus"
    GPU_QUANTITY = "gpu_quantity"
    BOM_COST = "bom_cost"


@dataclass(frozen=True)
class EvidenceBackedClaim:
    kind: ClaimKind
    value: object
    status: str
    evidence: tuple[EvidenceRef, ...]
    execution_trace: EvidenceChain

    @property
    def claim_id(self) -> str:
        return stable_id(
            "claim",
            self.kind.value,
            str(self.value),
            self.status,
            self.execution_trace.chain_id,
            tuple(ref.evidence_id for ref in self.evidence),
        )


def inspect_bom_claims(
    bom: Bom,
    canonical_candidates: tuple[str, ...],
    *,
    request_context: RequestContext,
) -> tuple[EvidenceBackedClaim, ...]:
    pipeline = run_bom_pipeline(
        bom,
        canonical_candidates,
        request_context=request_context,
    )
    decisions_by_mention = {decision.mention: decision for decision in pipeline.decisions}
    reconciled_by_key = {line.canonical_key: line for line in pipeline.reconciled_lines}

    all_lines = bom.lines
    gpu_lines = tuple(line for line in bom.lines if "gpu" in line.description.casefold())

    distinct = _claim(
        ClaimKind.DISTINCT_SKUS,
        all_lines,
        decisions_by_mention,
        pipeline.operational_lines,
        reconciled_by_key,
    )
    gpu = _claim(
        ClaimKind.GPU_QUANTITY,
        gpu_lines,
        decisions_by_mention,
        pipeline.operational_lines,
        reconciled_by_key,
    )
    cost = _claim(
        ClaimKind.BOM_COST,
        all_lines,
        decisions_by_mention,
        pipeline.operational_lines,
        reconciled_by_key,
    )
    return distinct, gpu, cost


def _claim(
    kind: ClaimKind,
    source_lines: tuple[BomLine, ...],
    decisions_by_mention: dict[str, ResolutionDecision],
    operational_lines: tuple[OperationalBomLine, ...],
    reconciled_by_key: dict[str, ReconciledLine],
) -> EvidenceBackedClaim:
    decisions = tuple(
        decisions_by_mention[line.sku] for line in source_lines if line.sku in decisions_by_mention
    )
    unresolved = any(decision.status is not ResolutionStatus.RESOLVED for decision in decisions)
    canonical_keys = {
        decision.canonical_key
        for decision in decisions
        if decision.status is ResolutionStatus.RESOLVED and decision.canonical_key is not None
    }
    relevant_operational = tuple(
        line for line in operational_lines if line.canonical_key in canonical_keys
    )
    relevant_reconciled = tuple(
        reconciled_by_key[key] for key in sorted(canonical_keys) if key in reconciled_by_key
    )
    evidence = tuple(line.evidence for line in source_lines)

    conflicts = any(line.status == "conflict" for line in relevant_reconciled)
    if unresolved or not source_lines or not relevant_reconciled:
        status = "unresolved"
    elif conflicts:
        status = "conflict"
    else:
        status = "reconciled"

    if kind is ClaimKind.DISTINCT_SKUS:
        value: object = None if status != "reconciled" else tuple(sorted(canonical_keys))
    elif kind is ClaimKind.GPU_QUANTITY:
        value = (
            None
            if status != "reconciled"
            else sum(
                (line.quantity for line in relevant_reconciled),
                Decimal(0),
            )
        )
    else:
        missing_price = any(line.unit_price is None for line in relevant_reconciled)
        if missing_price and status == "reconciled":
            status = "unresolved"
        value = (
            None
            if status != "reconciled"
            else sum(
                (
                    line.quantity * line.unit_price
                    for line in relevant_reconciled
                    if line.unit_price is not None
                ),
                Decimal(0),
            )
        )

    reconciliation_status = status if relevant_reconciled else "unresolved"
    trace = pipeline_chain(
        kind.value,
        evidence,
        decisions,
        relevant_operational,
        reconciliation_status,
    )
    return EvidenceBackedClaim(kind, value, status, evidence, trace)
