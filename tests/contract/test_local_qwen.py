"""Real local HTTP adapter contract without inference in deterministic CI."""

import json
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from procurement_intelligence_lab.adapters.local_qwen import LocalQwenInterpreter
from procurement_intelligence_lab.platform.semantics.interpretation import ModelFailure


@pytest.fixture
def endpoint() -> Generator[tuple[str, list[dict[str, object]]]]:
    requests: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(data)
            response = {
                "model": data["model"],
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "{}", "reasoning_content": "DO NOT RETAIN"},
                    }
                ],
                "usage": {"prompt_tokens": 123, "completion_tokens": 15},
            }
            raw = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_bounded_request_no_thinking_no_telemetry(
    endpoint: tuple[str, list[dict[str, object]]],
) -> None:
    url, requests = endpoint
    reply = LocalQwenInterpreter(endpoint=url).interpret(
        "Compare GPU-A", ("GPU-A",), "atlas", "2026-10-01T00:00:00+00:00"
    )
    assert reply.text == "{}" and reply.prompt_tokens == 123 and reply.completion_tokens == 15
    assert not hasattr(reply, "reasoning_content")
    data = requests[0]
    assert data["max_tokens"] == 256 and data["temperature"] == 0
    assert data["stream"] is False and data["chat_template_kwargs"] == {"enable_thinking": False}
    assert "response_format" in data and "tools" not in data


@pytest.mark.parametrize(
    "url",
    [
        "https://remote.example/v1",
        "http://localhost:8000/v1",
        "http://127.0.0.1:8000/v1?key=x",
        "http://user:secret@127.0.0.1:8000/v1",
        "http://127.0.0.1:8000/arbitrary",
        "http://[::1]:8000/v1",
    ],
)
def test_endpoint_is_explicit_numeric_loopback_only(url: str) -> None:
    with pytest.raises(ValueError):
        LocalQwenInterpreter(endpoint=url)


def test_transport_unavailable_is_typed(endpoint: tuple[str, list[dict[str, object]]]) -> None:
    with pytest.raises(ModelFailure):
        LocalQwenInterpreter(endpoint="http://127.0.0.1:1/v1").interpret(
            "Compare", ("GPU-A",), "atlas", "2026-10-01T00:00:00Z"
        )
