"""Typed, non-persistent review context for evidence-backed claims."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.application.evidence_service import (
    EvidenceBackedClaim,
    inspect_bom_claims,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


class ReviewReason(StrEnum):
    WRONG_RESULT = "wrong_result"
    SOURCE_ISSUE = "source_issue"
    MAPPING_ISSUE = "mapping_issue"
    RESOLUTION_ISSUE = "resolution_issue"
    STALE_RESULT = "stale_result"


@dataclass(frozen=True)
class ReviewContext:
    claim_id: str
    claim_kind: str
    claim_value: object
    claim_status: str
    evidence_ids: tuple[str, ...]
    chain_id: str
    node_ids: tuple[str, ...]
    allowed_reasons: tuple[ReviewReason, ...]


def review_context_for_claim(
    claim_id: str,
    bom: Bom,
    canonical_candidates: tuple[str, ...],
    *,
    request_context: RequestContext,
) -> ReviewContext:
    request_context.require(Permission.REVIEW)
    claims = inspect_bom_claims(
        bom,
        canonical_candidates,
        request_context=request_context,
    )
    claim = next((claim for claim in claims if claim.claim_id == claim_id), None)
    if claim is None:
        raise LookupError(f"unknown claim ID: {claim_id}")
    return _context_from_claim(claim)


def _context_from_claim(claim: EvidenceBackedClaim) -> ReviewContext:
    return ReviewContext(
        claim_id=claim.claim_id,
        claim_kind=claim.kind.value,
        claim_value=claim.value,
        claim_status=claim.status,
        evidence_ids=tuple(ref.evidence_id for ref in claim.evidence),
        chain_id=claim.execution_trace.chain_id,
        node_ids=tuple(node.node_id for node in claim.execution_trace.nodes),
        allowed_reasons=tuple(ReviewReason),
    )
