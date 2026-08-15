from typing import cast

import pytest

from procurement_intelligence_lab.domains.procurement.scope import Permission, RequestContext
from procurement_intelligence_lab.interfaces.web import (
    ReviewContextNotFoundError,
    claim_payload,
    review_context_payload,
)


def _context() -> RequestContext:
    return RequestContext(
        "demo-user",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset({Permission.READ_STATE, Permission.REVIEW}),
        "trace",
    )


def test_review_context_preserves_claim_and_trace_references() -> None:
    claim = claim_payload("How many GPUs are in the BOM?", request_context=_context())
    claim_id = cast(str, claim["claim_id"])

    context = review_context_payload(claim_id, request_context=_context())

    assert context["claim_id"] == claim_id
    assert context["claim_kind"] == "gpu_quantity"
    assert context["claim_value"] == "4"
    assert isinstance(context["chain_id"], str)
    assert len(cast(tuple[str, ...], context["evidence_ids"])) == 1
    assert len(cast(tuple[str, ...], context["node_ids"])) == 4
    assert cast(list[str], context["allowed_reasons"]) == [
        "wrong_result",
        "source_issue",
        "mapping_issue",
        "resolution_issue",
        "stale_result",
    ]


def test_review_context_rejects_unknown_claim_id() -> None:
    with pytest.raises(ReviewContextNotFoundError):
        review_context_payload("claim:missing", request_context=_context())
