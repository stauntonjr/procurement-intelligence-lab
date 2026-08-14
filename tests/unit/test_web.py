from typing import cast

import pytest

from procurement_intelligence_lab.domain.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.interfaces.web import (
    EvidenceNotFoundError,
    claim_payload,
    source_payload,
)


def _context(permission: Permission) -> RequestContext:
    return RequestContext(
        "demo-user",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset({permission, Permission.READ_STATE}),
        "trace",
    )


def test_claim_payload_exposes_trace_and_source_evidence() -> None:
    payload = claim_payload(
        "How many GPUs are in the BOM?",
        request_context=_context(Permission.READ_STATE),
    )

    assert payload["claim"] == "gpu_quantity"
    assert isinstance(payload["claim_id"], str)
    assert payload["value"] == "4"
    assert payload["status"] == "observed"
    evidence = cast(list[dict[str, object]], payload["evidence"])
    assert isinstance(evidence[0]["evidence_id"], str)
    assert evidence[0]["sheet"] == "BOM"
    execution_trace = cast(dict[str, object], payload["execution_trace"])
    assert isinstance(execution_trace["chain_id"], str)
    nodes = cast(list[dict[str, object]], execution_trace["nodes"])
    assert isinstance(nodes[0]["node_id"], str)
    assert [node["label"] for node in nodes] == [
        "source assertions",
        "entity resolution",
        "operational state",
        "reconciliation",
    ]


def test_source_payload_resolves_a_stable_evidence_id() -> None:
    claim = claim_payload(
        "How many GPUs are in the BOM?",
        request_context=_context(Permission.READ_STATE),
    )
    evidence = cast(list[dict[str, object]], claim["evidence"])
    evidence_id = cast(str, evidence[0]["evidence_id"])

    payload = source_payload(
        evidence_id,
        request_context=_context(Permission.READ_EVIDENCE),
    )
    source_evidence = cast(dict[str, object], payload["evidence"])
    source_line = cast(dict[str, object], payload["line"])

    assert source_evidence["evidence_id"] == evidence_id
    assert source_evidence["sheet"] == "BOM"
    assert source_line["sku"] == "GPU-A"


def test_source_payload_rejects_unknown_evidence_id() -> None:
    with pytest.raises(EvidenceNotFoundError):
        source_payload(
            "evidence:missing",
            request_context=_context(Permission.READ_EVIDENCE),
        )


def test_source_payload_rejects_missing_evidence_permission() -> None:
    with pytest.raises(ScopeAuthorizationError, match="lacks"):
        source_payload(
            "evidence:missing",
            request_context=_context(Permission.READ_STATE),
        )
