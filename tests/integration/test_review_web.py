"""Authenticated public HTTP review, not helper-only acceptance."""

import http.client
import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from typing import Any

import pytest

from procurement_intelligence_lab.interfaces.review_web import create_server

TOKEN = "test-only-capability-" + "x" * 48


@contextmanager
def server(path: Path, project: str = "atlas") -> Generator[tuple[str, int]]:
    web = create_server(path, project=project, token=TOKEN, port=0)
    thread = Thread(target=web.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", web.server_port
    finally:
        web.shutdown()
        web.server_close()
        thread.join()


def request(
    address: tuple[str, int],
    path: str,
    data: object = None,
    *,
    token: str | None = TOKEN,
    headers: dict[str, str] | None = None,
    raw: bytes | None = None,
) -> tuple[int, Any, dict[str, str]]:
    h = {"Authorization": "Bearer " + token} if token is not None else {}
    if data is not None or raw is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
    connection = http.client.HTTPConnection(*address, timeout=15)
    try:
        connection.request("POST" if body is not None else "GET", path, body=body, headers=h)
        response = connection.getresponse()
        payload = response.read().decode()
        return (
            response.status,
            json.loads(payload) if payload.startswith("{") else payload,
            dict(response.getheaders()),
        )
    finally:
        connection.close()


def start(address: tuple[str, int], item: str = "GPU-A") -> dict[str, Any]:
    status, view, _ = request(
        address, "/api/start", {"item": item, "as_of": "2026-10-01T00:00:00Z"}
    )
    assert status == 200, view
    return view


def review(view: dict[str, Any], decision: str = "approve") -> dict[str, str]:
    return {
        "run_id": view["run_id"],
        "brief_id": view["brief"]["brief_id"],
        "digest": view["brief"]["digest"],
        "decision": decision,
    }


def test_auth_before_work_and_transport_guards(tmp_path: Path) -> None:
    with server(tmp_path / "runs.db") as address:
        for token in (None, "wrong"):
            assert request(address, "/api/runs", token=token)[0] == 401
            assert (
                request(address, "/api/start", {"item": "GPU-A", "as_of": "bad"}, token=token)[0]
                == 401
            )
        with sqlite3.connect(tmp_path / "runs.db") as db:
            assert db.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 0
        for headers in (
            {"Origin": "https://foreign.example"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Host": "foreign.example"},
        ):
            assert request(address, "/api/runs", headers=headers)[0] == 403
        status, page, headers = request(address, "/", token=None)
        assert status == 200 and 'type="password"' in page
        assert "Fixture execution" in page and "Approve this finding" in page
        assert "Review finding" in page and "Evidence used for this finding" in page
        assert headers["Cache-Control"] == "no-store"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert TOKEN not in page
        assert (
            request(address, "/api/start", raw=b"{}", headers={"Content-Type": "text/plain"})[0]
            == 422
        )
        assert request(address, "/api/start", raw=b"x" * 8193)[0] == 422
        assert (
            request(
                address,
                "/api/start",
                raw=b'{"item":"GPU-A","item":"GPU-B","as_of":"2026-10-01T00:00:00Z"}',
            )[0]
            == 422
        )
        assert (
            request(
                address,
                "/api/start",
                {"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z", "project": "delta"},
            )[0]
            == 422
        )
        assert request(address, "/api/runs?project=delta")[0] == 422
        assert request(address, "/api/unknown")[0] == 404


def test_exact_review_restart_source_timeline_and_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    with server(path) as address:
        view = start(address)
        assert view["status"] == "awaiting_review"
        facts = json.loads(view["brief"]["content_json"])
        assert facts["required_quantity"] == "8" and facts["ordered_quantity"] == "6"
        run_id = view["run_id"]
        ref = facts["evidence"][0]
        status, source, _ = request(
            address, f"/api/source?run_id={run_id}&evidence_id={ref['evidence_id']}"
        )
        assert status == 200 and source["evidence"]["evidence_id"] == ref["evidence_id"]
        assert request(address, f"/api/source?run_id={run_id}&evidence_id=foreign")[0] == 404
        status, events, _ = request(address, f"/api/events?run_id={run_id}")
        assert status == 200 and events["events"][0]["kind"] == "run_started"
        assert any(e["kind"] == "tool_succeeded" for e in events["events"])
        for e in events["events"]:
            assert set(e) == {
                "event_id",
                "run_id",
                "query_id",
                "attempt_id",
                "occurred_at",
                "kind",
                "parent_id",
                "tool_name",
                "tool_version",
                "snapshot_id",
                "error_code",
            }
        wrong = review(view) | {"digest": "0" * 64}
        assert request(address, "/api/review", wrong)[0] == 409
        assert request(address, "/api/review", review(view) | {"approved": True})[0] == 422
    # A new server lifetime re-authenticates, discovers and recovers the persisted run.
    with server(path) as address:
        status, recent, _ = request(address, "/api/runs")
        assert status == 200 and recent["runs"][0]["run_id"] == run_id
        assert recent["runs"][0]["compatible"] is True
        assert request(address, "/api/recover", {"run_id": run_id})[1] == view
        status, saved, _ = request(address, "/api/review", review(view))
        assert status == 200 and saved["status"] == "completed"
        assert saved["saved"]["digest"] == view["brief"]["digest"]
        assert request(address, "/api/review", review(view))[1] == saved
        assert request(address, f"/api/run?run_id={run_id}")[1] == saved
        assert TOKEN not in json.dumps(saved)
    with server(path, project="delta") as address:
        assert request(address, "/api/runs")[1]["runs"] == []
        for route in ("run", "events", "source"):
            suffix = "&evidence_id=foreign" if route == "source" else ""
            assert request(address, f"/api/{route}?run_id={run_id}{suffix}")[0] == 404
        assert request(address, "/api/review", review(view))[0] == 404
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1


@pytest.mark.parametrize("item", ["GPU-C", "GPU-D", "GPU-E", "GPU-G"])
def test_uncertainty_and_numeric_facts_survive_public_review(tmp_path: Path, item: str) -> None:
    with server(tmp_path / "runs.db") as address:
        view = start(address, item)
        facts = json.loads(view["brief"]["content_json"])
        if item == "GPU-C":
            assert facts["required_quantity"] is None and facts["ordered_quantity"] is None
            assert facts["status"] == "not_assessed"
        status, rejected, _ = request(address, "/api/review", review(view, "reject"))
        assert status == 200 and rejected["status"] == "rejected" and rejected["saved"] is None
        assert request(address, "/api/review", review(view))[0] == 409


def test_invalid_and_unknown_requests_have_closed_errors(tmp_path: Path) -> None:
    with server(tmp_path / "runs.db") as address:
        for body in (
            {},
            {"item": "GPU-A", "as_of": "bad"},
            {"item": "GPU-A", "as_of": "2026-10-01"},
            {"item": 1, "as_of": None},
            {"item": "x" * 101, "as_of": "2026-10-01T00:00:00Z"},
        ):
            status, error, _ = request(address, "/api/start", body)
            assert status == 422 and set(error) == {"code", "category", "error"}
        assert (
            request(address, "/api/start", {"item": "absent", "as_of": "2026-10-01T00:00:00Z"})[0]
            == 422
        )
        assert request(address, "/api/run?run_id=unknown")[0] == 404
        assert request(address, "/api/run?run_id=one&run_id=two")[0] == 422
        assert (
            request(address, "/api/recover", {"run_id": "unknown", "checkpoint_id": "old"})[0]
            == 422
        )


def test_corrupt_checkpoint_is_hidden_from_unauthenticated_caller(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    with server(path) as address:
        view = start(address)
        checkpoint = path.with_name(path.name + ".checkpoints.sqlite")
        with sqlite3.connect(checkpoint) as db:
            db.execute("UPDATE checkpoints SET checkpoint=?", (b"PRIVATE_BYTES",))
        for route in ("run", "events"):
            assert request(address, f"/api/{route}?run_id={view['run_id']}", token=None)[0] == 401
        status, error, _ = request(address, f"/api/run?run_id={view['run_id']}")
        assert status == 503 and error["category"] == "infrastructure"
        assert "PRIVATE_BYTES" not in json.dumps(error)
        assert request(address, "/api/recover", {"run_id": view["run_id"]})[0] == 503


def test_private_token_file_and_no_external_bind(tmp_path: Path) -> None:
    from procurement_intelligence_lab.interfaces.review_web import read_token

    path = tmp_path / "token"
    path.write_text(TOKEN)
    path.chmod(0o600)
    assert read_token(path) == TOKEN
    path.chmod(0o644)
    with pytest.raises(ValueError):
        read_token(path)
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        read_token(link)
    path.write_text("short")
    with pytest.raises(ValueError):
        read_token(path)
    with pytest.raises(ValueError):
        create_server(tmp_path / "runs.db", project="atlas", token="short", port=0)


def test_public_expiry_changed_evidence_and_historical_version_discovery(tmp_path: Path) -> None:
    from dataclasses import replace
    from datetime import UTC, datetime, timedelta
    from unittest.mock import Mock

    from procurement_intelligence_lab.application.corpus_agent_tools import InvestigateToolArgs
    from procurement_intelligence_lab.platform.semantics.agent_runs import RunVersions

    path = tmp_path / "runs.db"
    web = create_server(path, project="atlas", token=TOKEN, port=0)
    thread = Thread(target=web.serve_forever, daemon=True)
    thread.start()
    address = ("127.0.0.1", web.server_port)
    try:
        view = start(address)
        app = web.composition
        now = datetime.now(UTC)
        app.service.clock = lambda: now
        app.service.review(
            view["run_id"],
            view["brief"]["brief_id"],
            view["brief"]["digest"],
            "approve",
            context=web.context,
        )
        app.service.clock = lambda: now + timedelta(hours=1)
        assert request(address, "/api/review", review(view))[0] == 409
        app.service.clock = lambda: now
        args = InvestigateToolArgs.from_mapping({"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"})
        original = app.service.tools.investigator.investigate(args.request, context=web.context)
        changed = Mock()
        changed.investigate.return_value = replace(original, snapshot_id="changed")
        app.service.tools = replace(app.service.tools, investigator=changed)
        assert request(address, "/api/review", review(view))[0] == 409
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 0
        versions = app.runs.versions
        app.runs.versions = RunVersions(
            versions.provider,
            versions.model,
            versions.prompt,
            versions.tool_schema,
            versions.fixture,
            "changed-app",
        )
        assert request(address, "/api/runs")[1]["runs"][0]["compatible"] is False
        assert request(address, f"/api/events?run_id={view['run_id']}")[0] == 409
        assert request(address, "/api/recover", {"run_id": view["run_id"]})[0] == 409
    finally:
        web.shutdown()
        web.server_close()
        thread.join()


def test_discover_and_recover_when_failed_start_has_no_displayable_brief(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from procurement_intelligence_lab.application.corpus_agent_tools import InvestigateToolArgs
    from procurement_intelligence_lab.application.exact_brief_review import BriefReviewService
    from procurement_intelligence_lab.platform.semantics.briefs import ReviewBrief
    from procurement_intelligence_lab.platform.semantics.scope import RequestContext
    from procurement_intelligence_lab.platform.semantics.workflows import WorkflowError

    original = BriefReviewService.draft
    failed = False

    def fail_once(
        self: BriefReviewService, run_id: str, args: InvestigateToolArgs, *, context: RequestContext
    ) -> ReviewBrief:
        nonlocal failed
        if not failed:
            failed = True
            raise WorkflowError("transient draft failure")
        return original(self, run_id, args, context=context)

    monkeypatch.setattr(BriefReviewService, "draft", fail_once)
    with server(tmp_path / "runs.db") as address:
        assert (
            request(address, "/api/start", {"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"})[0]
            == 503
        )
        history = request(address, "/api/runs")[1]["runs"]
        assert len(history) == 1
        run_id = history[0]["run_id"]
        assert request(address, f"/api/run?run_id={run_id}")[0] == 503
        status, recovered, _ = request(address, "/api/recover", {"run_id": run_id})
        assert status == 200 and recovered["status"] == "awaiting_review"
        assert recovered["run_id"] == run_id


def test_malformed_request_target_returns_closed_error(tmp_path: Path) -> None:
    import socket

    with (
        server(tmp_path / "runs.db") as address,
        socket.create_connection(address, timeout=5) as connection,
    ):
        connection.sendall(
            (
                f"GET http://[ HTTP/1.1\r\nHost: 127.0.0.1:{address[1]}\r\nAuthorization: Bearer {TOKEN}\r\n\r\n"
            ).encode()
        )
        response = http.client.HTTPResponse(connection)
        response.begin()
        assert response.status == 422
        assert json.loads(response.read())["code"] == "invalid_request_target"


def test_token_form_cannot_put_credentials_in_url_without_javascript(tmp_path: Path) -> None:
    from html.parser import HTMLParser

    class Forms(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.auth: dict[str, str | None] = {}

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            fields = dict(attrs)
            if tag == "form" and fields.get("id") == "auth":
                self.auth = fields

    with server(tmp_path / "runs.db") as address:
        _, page, _ = request(address, "/", token=None)
        form = Forms()
        form.feed(page)
        assert (form.auth.get("method") or "get").lower() == "post"
        target = form.auth.get("action")
        assert target == "/auth-unavailable"
        # Standard form fallback has no bearer header; it cannot authenticate or create work.
        assert (
            request(
                address,
                target,
                raw=("token=" + TOKEN).encode(),
                token=None,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )[0]
            == 401
        )
