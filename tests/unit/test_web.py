from typing import cast

from procurement_intelligence_lab.interfaces.web import claim_payload


def test_claim_payload_exposes_trace_and_source_evidence() -> None:
    payload = claim_payload("How many GPUs are in the BOM?")

    assert payload["claim"] == "gpu_quantity"
    assert payload["value"] == "4"
    assert payload["status"] == "observed"
    evidence = cast(list[dict[str, object]], payload["evidence"])
    assert evidence[0]["sheet"] == "BOM"
    execution_trace = cast(dict[str, object], payload["execution_trace"])
    nodes = cast(list[dict[str, object]], execution_trace["nodes"])
    assert [node["label"] for node in nodes] == [
        "source assertions",
        "entity resolution",
        "operational state",
        "reconciliation",
    ]
