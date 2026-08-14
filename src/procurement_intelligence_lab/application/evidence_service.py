"""Read-only claims and evidence service for inspector and chat adapters."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.application.pipeline import run_bom_pipeline
from procurement_intelligence_lab.domain.bom import (
    Bom,
    EvidenceRef,
    QueryResult,
    bom_cost,
    distinct_skus,
    gpu_quantity,
)
from procurement_intelligence_lab.domain.evidence import EvidenceChain
from procurement_intelligence_lab.domain.identity import stable_id
from procurement_intelligence_lab.domain.scope import RequestContext


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
    trace = run_bom_pipeline(
        bom,
        canonical_candidates,
        request_context=request_context,
    ).evidence
    queries: tuple[tuple[ClaimKind, QueryResult], ...] = (
        (ClaimKind.DISTINCT_SKUS, distinct_skus(bom)),
        (ClaimKind.GPU_QUANTITY, gpu_quantity(bom)),
        (ClaimKind.BOM_COST, bom_cost(bom)),
    )
    return tuple(
        EvidenceBackedClaim(kind, query.value, str(query.status), query.evidence, trace)
        for kind, query in queries
    )
