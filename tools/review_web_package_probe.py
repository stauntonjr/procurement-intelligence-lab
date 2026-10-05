"""Installed loopback HTTP caller, including a real server process restart."""

import http.client
import json
import secrets
import select
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit


@contextmanager
def running(database: Path, token_file: Path):
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.review_web",
            "--database",
            str(database),
            "--project",
            "atlas",
            "--token-file",
            str(token_file),
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=database.parent,
    )
    try:
        assert process.stdout is not None
        assert select.select([process.stdout], [], [], 15)[0], "server did not become ready"
        line = process.stdout.readline().strip()
        assert line.startswith("Fixture review at http://127.0.0.1:"), line
        yield urlsplit(line.removeprefix("Fixture review at "))
    finally:
        process.terminate()
        process.communicate(timeout=10)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="review-web-probe-") as directory:
        root = Path(directory)
        database = root / "runs.db"
        token_file = root / "token"
        token = secrets.token_urlsafe(48)
        token_file.write_text(token)
        token_file.chmod(0o600)

        def call(origin, path, data=None, authenticated=True):
            connection = http.client.HTTPConnection(origin.hostname, origin.port, timeout=15)
            headers = {"Authorization": "Bearer " + token} if authenticated else {}
            if data is not None:
                headers["Content-Type"] = "application/json"
            connection.request(
                "POST" if data is not None else "GET",
                path,
                json.dumps(data) if data is not None else None,
                headers,
            )
            response = connection.getresponse()
            status = response.status
            raw = response.read().decode()
            connection.close()
            return status, json.loads(raw) if raw.startswith("{") else raw

        with running(database, token_file) as origin:
            assert call(origin, "/", authenticated=False)[0] == 200
            assert call(origin, "/api/runs", authenticated=False)[0] == 401
            status, view = call(
                origin, "/api/start", {"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"}
            )
            assert status == 200 and view["status"] == "awaiting_review"
        with running(database, token_file) as origin:
            assert call(origin, "/api/runs")[1]["runs"][0]["run_id"] == view["run_id"]
            assert call(origin, "/api/recover", {"run_id": view["run_id"]}) == (200, view)
            brief = view["brief"]
            facts = json.loads(brief["content_json"])
            assert facts["required_quantity"] == "8" and facts["ordered_quantity"] == "6"
            payload = {
                "run_id": view["run_id"],
                "brief_id": brief["brief_id"],
                "digest": brief["digest"],
                "decision": "approve",
            }
            status, saved = call(origin, "/api/review", payload)
            assert status == 200 and saved["status"] == "completed"
            assert call(origin, "/api/review", payload) == (200, saved)
            assert token not in json.dumps(saved)
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1
    print("installed authenticated HTTP start/restart/recover/exact review/duplicate save passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
