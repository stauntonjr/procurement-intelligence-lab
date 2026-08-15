from decimal import Decimal

import pytest

from procurement_intelligence_lab.application.chat import (
    UnsupportedQuestionError,
    answer_question,
)
from procurement_intelligence_lab.application.evidence_service import ClaimKind
from procurement_intelligence_lab.domains.procurement.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domains.procurement.scope import Permission, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        "user", "tenant", "project", "site", frozenset({Permission.READ_STATE}), "trace"
    )


def bom() -> Bom:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B", "C", "D"))
    return Bom(
        "bom.xlsx",
        (
            BomLine("GPU-A", "GPU accelerator", Decimal(4), Decimal(100), evidence),
            BomLine("CPU-A", "CPU", Decimal(2), Decimal(50), evidence),
        ),
    )


def test_question_routes_to_evidence_backed_deterministic_claim() -> None:
    result = answer_question(
        "How many GPUs are in the BOM?",
        bom(),
        ("GPU-A", "CPU-A"),
        request_context=_context(),
    )

    assert result.kind is ClaimKind.GPU_QUANTITY
    assert result.value == Decimal(4)
    assert result.execution_trace.claim == "gpu_quantity"


def test_unapproved_question_abstains() -> None:
    with pytest.raises(UnsupportedQuestionError, match="no approved"):
        answer_question(
            "Which vendor should I choose?",
            bom(),
            ("GPU-A", "CPU-A"),
            request_context=_context(),
        )
