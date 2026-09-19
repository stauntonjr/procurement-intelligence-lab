import json
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest

from procurement_intelligence_lab.interfaces.web import InspectorHandler

HTTP_TIMEOUT_SECONDS = 5


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("name"):
            self.fields[str(values["name"])] = str(values.get("value", ""))


@pytest.mark.integration
def test_default_browser_form_completes_the_real_http_happy_path() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), InspectorHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = server.server_address
    host, port = str(address[0]), int(address[1])
    try:
        with urlopen(f"http://{host}:{port}/", timeout=HTTP_TIMEOUT_SECONDS) as response:
            parser = _FormParser()
            document = response.read().decode()
            parser.feed(document)
        assert "Original worksheet cells" in document
        with urlopen(
            f"http://{host}:{port}/api/ask?{urlencode(parser.fields)}",
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            payload = json.load(response)
            assert response.status == 200
        assert payload["claim"] == "gpu_quantity"
        assert payload["value"] == "4"
        assert payload["status"] == "reconciled"
        evidence = payload["evidence"][0]
        params = {key: value for key, value in parser.fields.items() if key != "q"}
        params["evidence_id"] = evidence["evidence_id"]
        with urlopen(
            f"http://{host}:{port}/api/source?{urlencode(params)}",
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            source = json.load(response)
        assert source["evidence"] == evidence
        assert source["line"]["sku"] == "GPU-A"
        assert source["line"]["quantity"] == payload["value"]
        assert source["evidence"]["row"] == 2
        assert source["evidence"]["cells"] == ["A", "B", "C", "D"]

        for changes, status in [
            ({"evidence_id": "evidence:unknown"}, 404),
            ({"tenant_id": "another-tenant"}, 403),
            ({"project_id": ""}, 403),
        ]:
            with pytest.raises(HTTPError) as error:
                urlopen(
                    f"http://{host}:{port}/api/source?{urlencode(params | changes)}",
                    timeout=HTTP_TIMEOUT_SECONDS,
                )
            assert error.value.code == status
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
