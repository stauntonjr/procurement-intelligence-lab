"""Exercise installed order scenarios over the actual HTTP boundary (stdlib only)."""

import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlencode
from urllib.request import urlopen

from procurement_intelligence_lab.interfaces.web import InspectorHandler


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), InspectorHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    params = {
        "tenant_id": "synthetic-tenant",
        "project_id": "synthetic-project",
        "site_id": "synthetic-site",
        "q": "How many GPUs are required?",
    }
    identities: list[str] = []
    try:
        for scenario, status, quantity in [
            ("order_mismatch", "quantity_mismatch", "2"),
            ("order_matched", "matched", "4"),
            ("order_missing", "not_assessed", None),
            ("order_unresolved", "not_assessed", "2"),
        ]:
            with urlopen(
                f"{base}/api/ask?{urlencode(params | {'scenario': scenario})}", timeout=5
            ) as response:
                payload = json.load(response)
            assert payload["status"] == status
            identities.append(payload["claim_id"])
            assert payload["comparison"]["ordered_quantity"] == quantity
            for evidence in payload["evidence"]:
                with urlopen(
                    f"{base}/api/source?{urlencode(params | {'evidence_id': evidence['evidence_id']})}",
                    timeout=5,
                ) as response:
                    source = json.load(response)
                assert source["evidence"] == evidence
                if evidence["evidence_id"] in payload["comparison"]["order_evidence_ids"]:
                    assert source["line"]["quantity"] == quantity
        for scenario, kind, lifecycle_status in [
            ("qualified_missing_po", "missing_po", "open"),
            ("incomplete_coverage", "coverage_gap", "open"),
            ("price_deviation", "price_deviation", "open"),
            ("late_commitment", "late_commitment", "open"),
            ("stale_revision", "stale_revision", "open"),
            ("substitution", "substitution", "open"),
            ("unresolved_identity", "unresolved_identity", "open"),
            ("lifecycle_suppressed", "quantity_mismatch", "suppressed"),
            ("lifecycle_reviewed", "quantity_mismatch", "in_review"),
            ("lifecycle_resolved", "quantity_mismatch", "resolved"),
        ]:
            query = params | {"scenario": scenario, "required_quantity": "999"}
            with urlopen(f"{base}/api/ask?{urlencode(query)}", timeout=5) as response:
                payload = json.load(response)
            selected = payload["selected_assessment"]
            identities.extend((payload["claim_id"], selected["anomaly"]["anomaly_id"]))
            assert selected["kind"] == kind
            assert selected["assessment_status"] == "anomaly"
            assert selected["lifecycle_status"] == lifecycle_status
            assert payload["inputs"]["required_quantity"] == "4"
            assert payload["read_only"] is True
            for evidence in payload["evidence"]:
                with urlopen(
                    f"{base}/api/source?{urlencode(query | {'evidence_id': evidence['evidence_id']})}",
                    timeout=5,
                ) as response:
                    source = json.load(response)
                assert source["evidence"] == evidence
                assert "source_record" in source or "source_grid" in source
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    print(json.dumps(sorted(identities)))


if __name__ == "__main__":
    main()
