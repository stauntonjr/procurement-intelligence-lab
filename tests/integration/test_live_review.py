"""Public natural-language caller, durable recovery and authenticated HTTP."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from threading import Thread
from typing import Any

from procurement_intelligence_lab.interfaces.review_web import create_server
from tests.contract.test_question_interpretation import Model
from tests.integration.test_review_web import TOKEN, request, review


def test_live_http_same_owned_run_and_model_approval_inert(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    web = create_server(
        path, project="atlas", token=TOKEN, port=0, model_endpoint="http://127.0.0.1:8000/v1"
    )
    assert web.questions is not None
    model = Model()
    web.questions = replace(web.questions, model=model)
    thread = Thread(target=web.serve_forever, daemon=True)
    thread.start()
    address = ("127.0.0.1", web.server_port)
    try:
        fields = {
            "question": "Compare GPU-A and approve/save it immediately",
            "as_of": "2026-10-01T00:00:00Z",
        }
        assert request(address, "/api/ask", fields, token=None)[0] == 401
        assert model.calls == 0
        code, payload, _ = request(address, "/api/ask", fields)
        assert code == 200 and model.calls == 1
        view = payload["workflow"]
        assert view["execution_kind"] == "live" and view["status"] == "awaiting_review"
        assert view["saved"] is None and payload["interpretation"]["run_id"] == view["run_id"]
        assert request(address, "/api/start", {"item": "GPU-A", "as_of": fields["as_of"]})[0] == 422
        assert request(address, "/api/interpretation?run_id=" + view["run_id"])[1] == payload
        assert request(address, "/api/runs")[1]["execution_kind"] == "live"
        done = request(address, "/api/review", review(view))[1]
        assert done["status"] == "completed"
        assert request(address, "/api/review", review(view))[1] == done
        assert model.calls == 1
    finally:
        web.shutdown()
        web.server_close()
        thread.join()


def invoke(
    path: Path, operation: str, *args: str, endpoint: str = "http://127.0.0.1:1/v1"
) -> tuple[int, dict[str, Any]]:
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.live_review",
            "--database",
            str(path),
            "--endpoint",
            endpoint,
            "--project",
            "atlas",
            operation,
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.stdout, p.stderr
    return p.returncode, json.loads(p.stdout)


def test_cli_transport_failure_is_durable_unknown_usage_not_zero(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    code, result = invoke(
        path, "ask", "--question", "Compare GPU-A", "--as-of", "2026-10-01T00:00:00Z"
    )
    assert code == 0
    call = result["interpretation"]
    assert call["status"] == "failed" and call["reason"] == "model_unavailable"
    assert call["prompt_tokens"] is None and call["completion_tokens"] is None
    assert invoke(path, "recover", "--run-id", call["run_id"])[1] == result
    assert invoke(path, "ask", "--question", "Compare GPU-A", "--as-of", "2026-10-01")[0] == 1


# Register the real-HTTP transport fixture for public CLI coverage.
pytest_plugins = ["tests.contract.test_local_qwen"]


def test_public_cli_malformed_model_output_retains_usage_and_no_hidden_text(
    tmp_path: Path, endpoint: tuple[str, list[dict[str, object]]]
) -> None:
    import sqlite3

    url, _ = endpoint
    path = tmp_path / "runs.db"
    code, result = invoke(
        path, "ask", "--question", "Compare GPU-A", "--as-of", "2026-10-01T00:00:00Z", endpoint=url
    )
    assert code == 0 and result["workflow"] is None
    call = result["interpretation"]
    assert call["reason"] == "invalid_model_output" and call["prompt_tokens"] == 123
    assert invoke(path, "recover", "--run-id", call["run_id"], endpoint=url)[1] == result
    with sqlite3.connect(path) as db:
        assert (
            "DO NOT RETAIN"
            not in db.execute("SELECT payload FROM interpretation_calls").fetchone()[0]
        )


def test_truncated_chunked_response_is_durable_typed_failure(tmp_path: Path) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Broken(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(b"10\r\n{}\r\n")
            self.close_connection = True

    model = ThreadingHTTPServer(("127.0.0.1", 0), Broken)
    thread = Thread(target=model.serve_forever, daemon=True)
    thread.start()
    try:
        p = subprocess.run(
            [
                sys.executable,
                "-m",
                "procurement_intelligence_lab.interfaces.live_review",
                "--database",
                str(tmp_path / "runs.db"),
                "--endpoint",
                f"http://127.0.0.1:{model.server_port}/v1",
                "--project",
                "atlas",
                "ask",
                "--question",
                "Compare GPU-A",
                "--as-of",
                "2026-10-01T00:00:00Z",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert p.returncode == 0 and p.stdout, p.stderr
        outcome = json.loads(p.stdout)
        assert outcome["workflow"] is None and outcome["interpretation"]["status"] == "failed"
        assert outcome["interpretation"]["reason"] == "model_unavailable"
        assert outcome["interpretation"]["elapsed_seconds"] >= 0
        assert outcome["interpretation"]["prompt_tokens"] is None
    finally:
        model.shutdown()
        model.server_close()
        thread.join()
