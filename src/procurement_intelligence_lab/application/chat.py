"""Constrained natural-language adapter over evidence-backed procurement claims."""

from procurement_intelligence_lab.application.evidence_service import (
    ClaimKind,
    EvidenceBackedClaim,
    inspect_bom_claims,
)
from procurement_intelligence_lab.domain.bom import Bom
from procurement_intelligence_lab.domain.scope import RequestContext


class UnsupportedQuestionError(ValueError):
    """Raised when a question has no approved deterministic claim route."""


def answer_question(
    question: str,
    bom: Bom,
    canonical_candidates: tuple[str, ...],
    *,
    request_context: RequestContext,
) -> EvidenceBackedClaim:
    normalized = " ".join(question.casefold().replace("-", " ").split())
    if "gpu" in normalized and any(token in normalized for token in ("how many", "quantity")):
        kind = ClaimKind.GPU_QUANTITY
    elif any(token in normalized for token in ("cost", "price", "total")):
        kind = ClaimKind.BOM_COST
    elif "sku" in normalized:
        kind = ClaimKind.DISTINCT_SKUS
    else:
        raise UnsupportedQuestionError("no approved deterministic claim route for this question")

    return next(
        claim
        for claim in inspect_bom_claims(
            bom,
            canonical_candidates,
            request_context=request_context,
        )
        if claim.kind is kind
    )
