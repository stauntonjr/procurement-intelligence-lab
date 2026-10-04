"""Loopback-only authenticated fixture review. No public or production identity."""

import argparse
import hmac
import json
import os
import secrets
import stat
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError
from procurement_intelligence_lab.application.corpus_agent_tools import (
    InvestigateToolArgs,
    ToolExecutionError,
)
from procurement_intelligence_lab.interfaces.agent_runs import PROJECTS
from procurement_intelligence_lab.interfaces.corpus_dto import source_dto
from procurement_intelligence_lab.interfaces.review_page import HTML
from procurement_intelligence_lab.interfaces.workflow import (
    WorkflowComposition,
    compose_services,
    view_dto,
)
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    RunConflict,
    RunNotFound,
    event_dto,
)
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefIntegrityError,
    BriefNotFound,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.workflows import WorkflowError, WorkflowRequest
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError, CorpusNotFoundError

MAX_BODY = 8192


def read_token(path: Path) -> str:
    """Read a caller-provided capability without symlinks or permissive files."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
        ):
            raise ValueError("token must be an owned private regular file")
        with os.fdopen(descriptor, "r", closefd=False) as stream:
            token = stream.read(513).strip()
        _validate_token(token)
        return token
    finally:
        os.close(descriptor)


def _validate_token(token: str) -> None:
    if not 32 <= len(token) <= 512 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("token must contain 32..512 non-whitespace ASCII characters")


def _fields(data: dict[str, Any], fields: set[str]) -> dict[str, str]:
    if set(data) != fields or any(
        type(v) is not str or not v.strip() or len(v) > 2000 for v in data.values()
    ):
        raise ValueError("invalid fields")
    return data


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _serialize(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError("unsupported public result")


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, database: Path, project: str, token: str, port: int) -> None:
        _validate_token(token)
        if project not in PROJECTS:
            raise ValueError("project is not admitted")
        self.token = token
        self.context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            project,
            "lab",
            frozenset(
                {Permission.READ_STATE, Permission.READ_EVIDENCE, Permission.REVIEW, Permission.ACT}
            ),
            "human-browser-review",
        )
        self.composition: WorkflowComposition = compose_services(database)
        super().__init__(("127.0.0.1", port), ReviewHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


def create_server(database: Path, *, project: str, token: str, port: int = 8001) -> ReviewServer:
    return ReviewServer(database, project, token, port)


class ReviewHandler(BaseHTTPRequestHandler):
    @property
    def review_server(self) -> ReviewServer:
        return cast(ReviewServer, self.server)

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format: str, *args: object) -> None:
        pass  # URLs, credentials and domain content do not enter access logs.

    def _send(self, status: int, data: object, *, page: bool = False) -> None:
        nonce = secrets.token_urlsafe(24)
        body = (
            str(data).replace("{{nonce}}", nonce).encode()
            if page
            else json.dumps(data, default=_serialize).encode()
        )
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if page else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, category: str) -> None:
        self._send(
            status,
            {
                "code": code,
                "category": category,
                "error": {
                    401: "Authenticate with the local reviewer token.",
                    403: "Request is outside the authorized local boundary.",
                    404: "Run, item or evidence was not found in this review scope.",
                    409: "Review conflicts with the exact brief, current evidence or run configuration.",
                    422: "Supply exactly the documented fields and a timezone-aware cutoff.",
                    503: "Workflow or admitted evidence is unavailable. Refresh or recover the run.",
                }[status],
            },
        )

    def _boundary(self) -> bool:
        origin = self.headers.get("Origin")
        if (
            self.headers.get("Host") != self.review_server.origin.removeprefix("http://")
            or origin is not None
            and origin != self.review_server.origin
            or self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin")
        ):
            self._error(403, "forbidden_transport", "authorization")
            return False
        return True

    def _authenticated(self) -> bool:
        values = self.headers.get_all("Authorization", [])
        if len(values) != 1 or not hmac.compare_digest(
            values[0].encode(), ("Bearer " + self.review_server.token).encode()
        ):
            self._error(401, "unauthenticated", "authorization")
            return False
        return True

    def _body(self) -> dict[str, Any]:
        lengths = self.headers.get_all("Content-Length", [])
        if (
            len(lengths) != 1
            or self.headers.get("Transfer-Encoding")
            or self.headers.get("Content-Type") != "application/json"
        ):
            raise ValueError("JSON with one content length required")
        size = int(lengths[0])
        if not 1 <= size <= MAX_BODY:
            raise ValueError("body size outside bound")
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise ValueError("incomplete body")
        data = json.loads(raw, object_pairs_hook=_pairs)
        if not isinstance(data, dict):
            raise TypeError("object required")
        return cast(dict[str, Any], data)

    def do_GET(self) -> None:
        self._dispatch(False)

    def do_POST(self) -> None:
        self._dispatch(True)

    def _dispatch(self, write: bool) -> None:
        if not self._boundary():
            return
        try:
            url = urlsplit(self.path)
            if url.scheme or url.netloc or url.fragment:
                raise ValueError("only local origin-form targets are supported")
        except ValueError:
            self._error(422, "invalid_request_target", "input")
            return
        if not write and url.path == "/" and not url.query:
            self._send(200, HTML, page=True)
            return
        if not self._authenticated():
            return
        try:
            context = self.review_server.context
            app = self.review_server.composition
            routes = (
                {"/api/start", "/api/recover", "/api/review"}
                if write
                else {"/api/runs", "/api/run", "/api/events", "/api/source"}
            )
            if url.path not in routes:
                raise CorpusNotFoundError("route not found")
            query = parse_qs(url.query, keep_blank_values=True)
            if write:
                if query:
                    raise ValueError("unexpected query")
                data = self._body()
                if url.path == "/api/start":
                    args = InvestigateToolArgs.from_mapping(
                        _fields(data, {"item", "as_of"})
                    ).request
                    result = app.runtime.start(
                        WorkflowRequest(args.canonical_key, args.as_of), context=context
                    )
                elif url.path == "/api/recover":
                    result = app.runtime.recover(
                        _fields(data, {"run_id"})["run_id"], context=context
                    )
                elif url.path == "/api/review":
                    fields = _fields(data, {"run_id", "brief_id", "digest", "decision"})
                    if fields["decision"] not in ("approve", "reject"):
                        raise ValueError("invalid decision")
                    result = app.runtime.review(
                        fields["run_id"],
                        fields["brief_id"],
                        fields["digest"],
                        fields["decision"],
                        context=context,
                    )
                else:
                    raise CorpusNotFoundError("route not found")
                self._send(200, view_dto(result))
                return
            if url.path == "/api/runs":
                if query:
                    raise ValueError("unexpected query")
                self._send(
                    200,
                    {
                        "project": context.project_id,
                        "execution_kind": "fixture",
                        "runs": [
                            {
                                "run_id": run.run_id,
                                "created_at": run.created_at.isoformat(),
                                "execution_kind": run.execution_kind.value,
                                "compatible": run.versions == app.runs.versions
                                and run.execution_kind == app.runs.execution_kind,
                            }
                            for run in app.runs.recent(context=context)
                        ],
                    },
                )
                return
            keys = {"run_id", "evidence_id"} if url.path == "/api/source" else {"run_id"}
            if any(len(v) != 1 for v in query.values()):
                raise ValueError("duplicate query field")
            fields = _fields({k: v[0] for k, v in query.items()}, keys)
            run_id = fields["run_id"]
            if url.path == "/api/run":
                payload = view_dto(app.runtime.status(run_id, context=context))
            elif url.path == "/api/events":
                context.require(Permission.READ_EVIDENCE)
                payload = {
                    "events": [event_dto(e) for e in app.runs.events(run_id, context=context)]
                }
            elif url.path == "/api/source":
                brief = app.service.get(run_id, None, context=context)
                facts = json.loads(brief.content_json)
                if fields["evidence_id"] not in {ref["evidence_id"] for ref in facts["evidence"]}:
                    raise CorpusNotFoundError("evidence outside brief")
                payload = source_dto(
                    app.reader.source_by_id(fields["evidence_id"], context=context)
                )
            else:
                raise CorpusNotFoundError("route not found")
            self._send(200, payload)
        except (RunNotFound, BriefNotFound, CorpusNotFoundError):
            self._error(404, "not_found", "input")
        except ScopeAuthorizationError:
            self._error(403, "forbidden_scope", "authorization")
        except (RunConflict, BriefConflict) as error:
            self._error(409, error.code.value, error.category.value)
        except (WorkflowError, RunStoreError, BriefIntegrityError, ToolExecutionError) as error:
            status = (
                409
                if error.category.value == "policy"
                else 503
                if error.category.value in ("infrastructure", "transient")
                else 422
            )
            self._error(status, error.code.value, error.category.value)
        except CorpusAdmissionError:
            self._error(503, "corpus_admission_failed", "infrastructure")
        except (ValueError, TypeError, UnicodeError, RecursionError):
            self._error(422, "invalid_request", "input")
        except TimeoutError:
            self._error(422, "incomplete_body", "input")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--project", choices=PROJECTS, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    try:
        with create_server(
            args.database, project=args.project, token=read_token(args.token_file), port=args.port
        ) as server:
            print(f"Fixture review at {server.origin}", flush=True)
            server.serve_forever()
    except (ValueError, OSError, WorkflowError, RunStoreError, BriefIntegrityError):
        print(json.dumps({"code": "local_review_unavailable", "category": "infrastructure"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
