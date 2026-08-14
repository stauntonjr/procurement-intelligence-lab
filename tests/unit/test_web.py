from typing import cast

from procurement_intelligence_lab.interfaces.web import claim_payload


def test_claim_payload_exposes_trace_and_source_evidence() -> None:
    payload = claim_payload("How many GPUs are in the BOM?")

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
