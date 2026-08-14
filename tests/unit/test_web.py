from procurement_intelligence_lab.interfaces.web import claim_payload


def test_claim_payload_exposes_trace_and_source_evidence() -> None:
    payload = claim_payload("How many GPUs are in the BOM?")

    assert payload["claim"] == "gpu_quantity"
    assert payload["value"] == "4"
    assert payload["status"] == "observed"
    assert payload["evidence"][0]["sheet"] == "BOM"
    assert [node["label"] for node in payload["execution_trace"]["nodes"]] == [
        "source assertions",
        "entity resolution",
        "operational state",
        "reconciliation",
    ]
