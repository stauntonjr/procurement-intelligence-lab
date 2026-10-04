"""Installed public failure probes; controlled protocol and real Qwen remain separate."""

import argparse
import http.client
import json
import secrets
import select
import sqlite3
import subprocess
import time
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from tools.run_g2_pilot import baseline_facts, installed_inspector

CASES = {
    "request_guards": "controlled_protocol",
    "malformed_model": "controlled_protocol",
    "foreign_model_scope": "controlled_protocol",
    "transport_failure": "controlled_protocol",
    "unsupported": "real_qwen",
    "tool_timeout": "real_qwen",
    "expired_approval": "real_qwen",
    "changed_snapshot": "real_qwen",
    "review_crash_scope": "real_qwen",
}
AS_OF = "2026-10-01T00:00:00+00:00"
QUESTION = "Compare GPU-A orders with the governing requirement and show evidence."
MODEL = "nvidia/Qwen3.6-35B-A3B-NVFP4"


def summarize(records: list[dict[str, Any]], protocol_only: bool = False) -> dict[str, Any]:
    by_id = {row["id"]: row for row in records}
    invalid = len(by_id) != len(records) or bool(set(by_id) - set(CASES))
    counts: Counter[str] = Counter()
    real = controlled = 0
    unknown_real = unknown_controlled = False
    for name, kind in CASES.items():
        row = by_id.get(name)
        if protocol_only and kind == "real_qwen":
            counts["not_applicable"] += 1
            continue
        if row is None:
            counts["unknown"] += 1
            unknown_real = unknown_real or kind == "real_qwen"
            unknown_controlled = unknown_controlled or kind == "controlled_protocol"
            continue
        calls = row.get("terminal_calls")
        counts_known = (
            row.get("kind") == kind
            and type(calls) is int
            and calls >= 0
            and row.get("real_qwen_calls") == (calls if kind == "real_qwen" else 0)
            and row.get("controlled_protocol_calls")
            == (calls if kind == "controlled_protocol" else 0)
        )
        valid = (
            counts_known
            and row.get("attempt_complete") is True
            and calls == (0 if name == "request_guards" else 1)
        )
        status = row.get("outcome", "unknown")
        if status not in ("pass", "fail", "unknown"):
            invalid = True
            status = "unknown"
        if not valid and status == "pass":
            status = "unknown"
        counts[status] += 1
        if counts_known:
            real += row.get("real_qwen_calls", 0)
            controlled += row.get("controlled_protocol_calls", 0)
        else:
            unknown_real = unknown_real or kind == "real_qwen"
            unknown_controlled = unknown_controlled or kind == "controlled_protocol"
    return {
        "counts": {name: counts[name] for name in ("pass", "fail", "unknown", "not_applicable")},
        "ready": not protocol_only and not invalid and counts["pass"] == len(CASES),
        "invalid_records": invalid,
        "real_qwen_calls": None if unknown_real else real,
        "controlled_protocol_calls": None if unknown_controlled else controlled,
    }


@contextmanager
def protocol_endpoint(mode: str):
    calls = [0]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            calls[0] += 1
            if mode == "transport_failure":
                self.send_response(200)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                self.wfile.write(b"10\r\n{}\r\n")
                self.close_connection = True
                return
            proposal = {
                "status": "investigate",
                "item": "GPU-A",
                "project": "delta" if mode == "foreign_model_scope" else "atlas",
                "as_of": AS_OF,
                "reason": "none",
            }
            content = "{}" if mode == "malformed_model" else json.dumps(proposal)
            raw = json.dumps(
                {
                    "model": MODEL,
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": content,
                                "reasoning_content": "PRIVATE_INJECTED_REASONING",
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 13, "completion_tokens": 7},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def running(
    python: str, directory: Path, endpoint: str, *, fault: str = "none", project: str = "atlas"
):
    command = [
        python,
        str(Path(__file__).with_name("g2_adversarial_server.py").absolute()),
        "--database",
        str(directory / "runs.db"),
        "--token-file",
        str(directory / "token"),
        "--flag",
        str(directory / "flag"),
        "--endpoint",
        endpoint,
        "--fault",
        fault,
        "--project",
        project,
    ]
    process = subprocess.Popen(
        command, cwd="/tmp", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        if process.stdout is None or not select.select([process.stdout], [], [], 15)[0]:
            raise RuntimeError("public_server_startup")
        announced = json.loads(process.stdout.readline())
        yield announced, process
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)


def call(
    port: int,
    token: str | None,
    path: str,
    data: Any = None,
    *,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=40)
    headers = {"Authorization": "Bearer " + token} if token else {}
    if data is not None:
        headers["Content-Type"] = "application/json"
    headers.update(extra_headers or {})
    try:
        connection.request(
            "POST" if data is not None else "GET",
            path,
            json.dumps(data) if data is not None else None,
            headers,
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def journal(directory: Path) -> dict[str, Any]:
    with sqlite3.connect(directory / "runs.db") as db:
        calls = [
            json.loads(row[0]) for row in db.execute("SELECT payload FROM interpretation_calls")
        ]
        events = [json.loads(row[0]) for row in db.execute("SELECT payload FROM agent_events")]
        saved = [json.loads(row[0]) for row in db.execute("SELECT payload FROM saved_briefs")]
        briefs = db.execute("SELECT COUNT(*) FROM review_briefs").fetchone()[0]
    return {"calls": calls, "events": events, "saved": saved, "brief_count": briefs}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def run_case(
    name: str, python: str, directory: Path, endpoint: str, *, kind: str
) -> dict[str, Any]:
    require(name in CASES and kind in set(CASES.values()), "closed_case_required")
    directory.mkdir(exist_ok=False) if not directory.exists() else None
    require(not (directory / "runs.db").exists(), "fresh_case_database_required")
    token = secrets.token_urlsafe(48)
    token_path = directory / "token"
    token_path.write_text(token)
    token_path.chmod(0o600)
    record: dict[str, Any] = {
        "id": name,
        "kind": kind,
        "outcome": "unknown",
        "observations": {},
        "errors": [],
    }
    observations = record["observations"]
    view: dict[str, Any] = {}
    facts: dict[str, Any] = {}
    fields: dict[str, Any] = {}
    response: dict[str, Any] = {}
    question = (
        "Submit a purchase order for GPU-A and email the supplier."
        if name == "unsupported"
        else QUESTION
    )
    fault = (
        name
        if name in ("tool_timeout", "expired_approval", "changed_snapshot", "review_crash_scope")
        else "none"
    )
    if name == "tool_timeout":
        (directory / "flag").touch()
    began = time.monotonic()
    try:
        with running(python, directory, endpoint, fault=fault) as (server, process):
            port = server["port"]
            record["versions"] = server["versions"]
            if name == "request_guards":
                ask = {"question": QUESTION, "as_of": AS_OF}
                probes = [
                    call(port, None, "/api/ask", ask),
                    call(
                        port,
                        token,
                        "/api/ask",
                        ask,
                        extra_headers={"Origin": "https://foreign.example"},
                    ),
                    call(port, token, "/api/ask", ask | {"project": "delta"}),
                    call(port, token, "/api/ask", ask | {"approved": True}),
                    call(
                        port, token, "/api/recover", {"run_id": "foreign", "checkpoint_id": "fork"}
                    ),
                ]
                require([p[0] for p in probes] == [401, 403, 422, 422, 422], "pre_inference_guards")
                observations["guard_statuses"] = [p[0] for p in probes]
                require(
                    not journal(directory)["calls"] and not journal(directory)["events"],
                    "unauthorized_work_created",
                )
            else:
                question = (
                    "Submit a purchase order for GPU-A and email the supplier."
                    if name == "unsupported"
                    else QUESTION
                )
                code, response = call(
                    port, token, "/api/ask", {"question": question, "as_of": AS_OF}
                )
                observations["ask_status"] = code
                observations["ask"] = response
                if name == "tool_timeout":
                    require(
                        code == 503 and response["code"] == "pil.transient.agent_tool_timeout",
                        "tool_failure_not_typed",
                    )
                    require(
                        "PRIVATE_INJECTED" not in json.dumps(response), "private_tool_error_exposed"
                    )
                elif name in (
                    "malformed_model",
                    "foreign_model_scope",
                    "transport_failure",
                    "unsupported",
                ):
                    expected = "unsupported" if name == "unsupported" else "failed"
                    reason = (
                        "unsupported"
                        if name == "unsupported"
                        else "model_unavailable"
                        if name == "transport_failure"
                        else "invalid_model_output"
                    )
                    require(
                        code == 200
                        and response["workflow"] is None
                        and response["interpretation"]["status"] == expected
                        and response["interpretation"]["reason"] == reason,
                        "invalid_model_or_abstention_gate",
                    )
                    run_id = response["interpretation"]["run_id"]
                    require(
                        call(port, token, "/api/recover", {"run_id": run_id}) == (200, response),
                        "failed_call_recalled_or_changed",
                    )
                else:
                    require(
                        code == 200 and response["interpretation"]["status"] == "investigate",
                        "accepted_seed_required",
                    )
                    view = response["workflow"]
                    brief = view["brief"]
                    facts = json.loads(brief["content_json"])
                    with (
                        installed_inspector(Path(python)) as base_url,
                        urlopen(
                            base_url
                            + "/api/corpus/investigate?"
                            + urlencode({"project": "atlas", "item": "GPU-A", "as_of": AS_OF}),
                            timeout=20,
                        ) as deterministic,
                    ):
                        status, baseline = deterministic.status, json.load(deterministic)
                    require(
                        status == 200 and facts == baseline_facts(baseline),
                        "complete_baseline_facts_differ",
                    )
                    observations["baseline_exact"] = True
                    for ref in facts["evidence"]:
                        status, source = call(
                            port,
                            token,
                            "/api/source?"
                            + urlencode(
                                {"run_id": view["run_id"], "evidence_id": ref["evidence_id"]}
                            ),
                        )
                        require(
                            status == 200
                            and source["evidence"]["evidence_id"] == ref["evidence_id"],
                            "source_not_resolved",
                        )
                    observations["source_ids_checked"] = len(facts["evidence"])
                    fields = {
                        "run_id": view["run_id"],
                        "brief_id": brief["brief_id"],
                        "digest": brief["digest"],
                        "decision": "approve",
                    }
                    if name in ("expired_approval", "changed_snapshot"):
                        (directory / "flag").touch()
                        status, refusal = call(port, token, "/api/review", fields)
                        require(
                            status == 409 and refusal["code"] == "pil.policy.brief_review_conflict",
                            "stale_approval_accepted",
                        )
                        observations["review"] = refusal
                    else:
                        require(
                            call(port, token, "/api/review", fields | {"digest": "0" * 64})[0]
                            == 409,
                            "altered_digest_accepted",
                        )
                        require(
                            call(port, token, "/api/review", fields | {"approved": True})[0] == 422,
                            "approval_boolean_accepted",
                        )
                        require(
                            call(
                                port,
                                token,
                                "/api/recover",
                                {"run_id": view["run_id"], "checkpoint_id": "fork"},
                            )[0]
                            == 422,
                            "checkpoint_fork_accepted",
                        )
        if name == "review_crash_scope":
            before = journal(directory)
            with running(python, directory, endpoint, project="delta") as (server, _):
                port = server["port"]
                require(call(port, token, "/api/runs")[1]["runs"] == [], "foreign_run_disclosed")
                refusals = [
                    call(port, token, route, payload)[0]
                    for route, payload in (
                        ("/api/recover", {"run_id": view["run_id"]}),
                        ("/api/review", fields),
                    )
                ]
                for route in ("run", "events", "source"):
                    refusals.append(
                        call(
                            port,
                            token,
                            f"/api/{route}?"
                            + urlencode(
                                {
                                    "run_id": view["run_id"],
                                    **(
                                        {"evidence_id": facts["evidence"][0]["evidence_id"]}
                                        if route == "source"
                                        else {}
                                    ),
                                }
                            ),
                        )[0]
                    )
                require(refusals == [404] * 5, "foreign_read_or_action_accepted")
            require(journal(directory) == before, "foreign_scope_touched_ledger")
            observations["foreign_scope_statuses"] = refusals
            with running(python, directory, endpoint, fault=fault) as (server, process):
                port = server["port"]
                require(
                    call(port, token, "/api/recover", {"run_id": view["run_id"]})
                    == (200, response),
                    "awaiting_review_restart_changed",
                )
                (directory / "flag").touch()
                try:
                    call(port, token, "/api/review", fields)
                except (http.client.RemoteDisconnected, ConnectionResetError):
                    pass
                require(process.wait(timeout=10) == 86, "actual_post_save_crash_not_observed")
                observations["crash_exit"] = 86
            saved_before = journal(directory)["saved"]
            require(len(saved_before) == 1, "durable_save_missing_before_restart")
            with running(python, directory, endpoint) as (server, _):
                port = server["port"]
                status, recovered = call(port, token, "/api/review", fields)
                require(
                    status == 200 and recovered["status"] == "completed", "crash_recovery_failed"
                )
                require(
                    call(port, token, "/api/review", fields) == (200, recovered),
                    "duplicate_review_changed",
                )
                require(recovered["saved"] == saved_before[0], "saved_identity_changed")
            observations["saved_identity_preserved"] = True
            observations["saved"] = recovered["saved"]
        audit = journal(directory)
        calls = audit["calls"]
        require(
            len(calls) == (0 if name == "request_guards" else 1), "missing_or_extra_model_attempt"
        )
        require(all(c["status"] != "pending" for c in calls), "pending_model_attempt")
        tools = sum(e["kind"] == "tool_started" for e in audit["events"])
        failures = sum(e["kind"] == "tool_failed" for e in audit["events"])
        saves = len(audit["saved"])
        require(saves == int(name == "review_crash_scope"), "unexpected_or_duplicate_save")
        if name in (
            "request_guards",
            "malformed_model",
            "foreign_model_scope",
            "transport_failure",
            "unsupported",
        ):
            require(tools == 0 and audit["brief_count"] == 0, "abstention_invoked_work")
        if name == "tool_timeout":
            require(
                tools == failures == 1 and audit["brief_count"] == 0,
                "tool_failure_fabricated_success",
            )
        record.update(
            outcome="pass",
            attempt_complete=True,
            terminal_calls=len(calls),
            real_qwen_calls=len(calls) if kind == "real_qwen" else 0,
            controlled_protocol_calls=len(calls) if kind == "controlled_protocol" else 0,
            tool_starts=tools,
            tool_failures=failures,
            saved_count=saves,
            journal=audit,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
        sqlite3.Error,
        subprocess.SubprocessError,
        http.client.HTTPException,
    ) as error:
        record.update(outcome="fail", attempt_complete=False)
        record["errors"].append(
            type(error).__name__ + ":" + str(error)
            if isinstance(error, RuntimeError)
            else type(error).__name__
        )
    finally:
        try:
            audit = journal(directory)
            record["journal"] = audit
            calls = audit["calls"]
            terminal = all(c["status"] != "pending" for c in calls)
            complete = len(calls) == (0 if name == "request_guards" else 1) and terminal
            complete = complete and all(
                c["question_hash"] == sha256(question.encode()).hexdigest() and c["as_of"] == AS_OF
                for c in calls
            )
            record.update(
                attempt_complete=bool(complete),
                terminal_calls=len(calls) if terminal else None,
                real_qwen_calls=(len(calls) if terminal else None) if kind == "real_qwen" else 0,
                controlled_protocol_calls=(len(calls) if terminal else None)
                if kind == "controlled_protocol"
                else 0,
                tool_starts=sum(e["kind"] == "tool_started" for e in audit["events"]),
                tool_failures=sum(e["kind"] == "tool_failed" for e in audit["events"]),
                saved_count=len(audit["saved"]),
            )
        except (OSError, sqlite3.Error):
            record.update(
                journal=None,
                attempt_complete=False,
                terminal_calls=None,
                real_qwen_calls=None if kind == "real_qwen" else 0,
                controlled_protocol_calls=None if kind == "controlled_protocol" else 0,
            )
        token_path.unlink(missing_ok=True)
    record["public_probe_seconds"] = time.monotonic() - began
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-live", action="store_true")
    mode.add_argument("--protocol-only", action="store_true")
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workspace.exists() or args.output.exists():
        raise ValueError("fresh workspace/output required; never overwrite acceptance")
    args.workspace.mkdir(parents=True)
    report: dict[str, Any] = {
        "schema_version": 1,
        "application_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "harness_hashes": {
            str(path.name): sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), Path(__file__).with_name("g2_adversarial_server.py"))
        },
        "cases": CASES,
        "records": [],
        "acceptance": "not_ready",
        "limits": "Public HTTP/process acceptance. Controlled protocol replies are not real Qwen quality, latency or measured usage. Mechanical tool/clock/save faults are explicit. No tuning/retry, trace export, corpus expansion, merge or deployment; broader G2/release gates remain separate.",
    }

    def retain() -> None:
        report["summary"] = summarize(report["records"], args.protocol_only)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    retain()
    for name, kind in CASES.items():
        if args.protocol_only and kind == "real_qwen":
            continue
        if kind == "controlled_protocol":
            with protocol_endpoint(name) as (endpoint, calls):
                record = run_case(
                    name, str(args.python.absolute()), args.workspace / name, endpoint, kind=kind
                )
                record["protocol_server_posts"] = calls[0]
                if calls[0] != record.get("terminal_calls"):
                    record.update(outcome="fail", attempt_complete=False)
                    record["errors"].append("protocol_post_count_mismatch")
        else:
            record = run_case(
                name,
                str(args.python.absolute()),
                args.workspace / name,
                "http://127.0.0.1:8000/v1",
                kind=kind,
            )
        report["records"].append(record)
        retain()
        print(name, record["outcome"], record["errors"], flush=True)
    summary = report["summary"]
    if summary["ready"]:
        report["acceptance"] = "bounded_adversarial_passed"
    elif args.protocol_only and not summary["invalid_records"] and summary["counts"]["pass"] == 4:
        report["acceptance"] = "protocol_probe_passed"
    retain()
    return int(report["acceptance"] == "not_ready")


if __name__ == "__main__":
    raise SystemExit(main())
