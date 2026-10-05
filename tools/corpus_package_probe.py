"""Exercise installed corpus HTTP and source resources outside the checkout."""

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
    try:
        identities = []
        for project, item, required, ordered in (
            ("atlas", "GPU-A", "8", "6"),
            ("borealis", "ACC-B1", "12", "8"),
            ("cinder", "NIC-C1", "10", "12"),
            ("delta", "STORE-D1", "24", "20"),
        ):
            with urlopen(
                base
                + "/api/corpus/investigate?"
                + urlencode(
                    {"project": project, "item": item, "as_of": "2026-10-01T00:00:00+00:00"}
                )
            ) as response:
                result = json.load(response)
            assert (result["status"], result["required_quantity"], result["ordered_quantity"]) == (
                "anomaly",
                required,
                ordered,
            )
            assert len(result["evidence"]) == 12
            for ref in result["evidence"]:
                with urlopen(base + ref["url"]) as response:
                    source = json.load(response)
                assert source["evidence"]["evidence_id"] == ref["evidence_id"]
            identities.append(
                {
                    "snapshot_id": result["snapshot_id"],
                    "assessment_id": result["assessment_id"],
                    "evidence_ids": [r["evidence_id"] for r in result["evidence"]],
                }
            )
        print(json.dumps(identities, sort_keys=True))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
