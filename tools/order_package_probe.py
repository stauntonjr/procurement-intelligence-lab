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
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
