import json
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from threading import Thread
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
            parser.feed(response.read().decode())
        with urlopen(
            f"http://{host}:{port}/api/ask?{urlencode(parser.fields)}",
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            payload = json.load(response)
            assert response.status == 200
        assert payload["claim"] == "gpu_quantity"
        assert payload["value"] == "4"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
