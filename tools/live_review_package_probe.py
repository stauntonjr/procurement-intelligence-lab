"""Installed CLI/local HTTP intent contract with a deterministic model transport double.

Not live inference acceptance; never include these calls in live metrics.
"""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread


def main() -> None:
    calls: list[object] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body)
            context = json.loads(body["messages"][1]["content"])
            proposal = {
                "status": "investigate",
                "item": "GPU-A",
                "project": context["project"],
                "as_of": context["as_of"],
                "reason": "none",
            }
            payload = json.dumps(
                {
                    "model": body["model"],
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 40},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory() as temporary:
            db = Path(temporary) / "live.db"
            base = [
                sys.executable,
                "-m",
                "procurement_intelligence_lab.interfaces.live_review",
                "--database",
                str(db),
                "--endpoint",
                f"http://127.0.0.1:{server.server_port}/v1",
                "--project",
                "atlas",
            ]

            def invoke(*args: str) -> dict:
                result = subprocess.run(
                    [*base, *args], capture_output=True, text=True, check=True, timeout=40
                )
                return json.loads(result.stdout)

            outcome = invoke(
                "ask", "--question", "Compare GPU-A", "--as-of", "2026-10-01T00:00:00Z"
            )
            view = outcome["workflow"]
            brief = view["brief"]
            assert view["execution_kind"] == "live" and view["status"] == "awaiting_review"
            facts = json.loads(brief["content_json"])
            assert facts["required_quantity"] == "8" and facts["ordered_quantity"] == "6"
            assert invoke("recover", "--run-id", view["run_id"]) == outcome
            args = [
                "review",
                "--run-id",
                view["run_id"],
                "--brief-id",
                brief["brief_id"],
                "--digest",
                brief["digest"],
                "--decision",
                "approve",
            ]
            done = invoke(*args)
            assert done["status"] == "completed" and invoke(*args) == done
            assert len(calls) == 1
            events = invoke("events", "--run-id", view["run_id"])["events"]
            assert sum(e["kind"] == "tool_succeeded" for e in events) == 2
            print(
                "installed live-intent CLI transport contract, exact review and restart passed; model double, no live acceptance"
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
