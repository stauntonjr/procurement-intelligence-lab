"""Explicit local Qwen pilot over frozen questions and clean installed public callers."""

import argparse
import json
import select
import sqlite3
import subprocess
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from procurement_intelligence_lab.adapters.sqlite_interpretation import SqliteInterpretationStore
from procurement_intelligence_lab.application.agent_trajectory import evaluate_trajectory
from procurement_intelligence_lab.interfaces.live_review import compose_live
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEvent,
    AgentEventKind,
    AgentRun,
    run_dto,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from tools.evaluate_procurement_corpus import DATASET, _fetch, evaluate
from tools.g2_pilot_scoring import PILOT, load_pilot, score_intent, summarize


class PublicFailure(RuntimeError):
    pass


def baseline_facts(response: dict[str, Any]) -> dict[str, Any]:
    return {
        k: ([{a: b for a, b in ref.items() if a != "url"} for ref in v] if k == "evidence" else v)
        for k, v in response.items()
        if k not in {"project", "governance_candidates"}
    }


def require_live_run(
    run: dict[str, Any], case: dict[str, Any], run_id: str, versions: dict[str, Any]
) -> None:
    if (
        run.get("execution_kind") != "live"
        or run.get("run_id") != run_id
        or run.get("project_id") != case["project"]
        or run.get("principal_id") != "local-demo"
        or run.get("tenant_id") != "synthetic-tenant"
        or run.get("site_id") != "lab"
        or run.get("versions") != versions
    ):
        raise ValueError("foreign/fixture/version-incompatible run")


def evaluate_case(
    case: dict[str, Any],
    expected: dict[str, Any],
    invoke: Callable[..., dict[str, Any]],
    audit: Callable[..., dict[str, Any]],
    retain: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": case["id"],
        "outcome": "unknown",
        "errors": [],
        "model_calls": None,
        "phase": "before_ask",
    }
    began = time.monotonic()
    retain(dict(record))
    try:
        outcome = invoke("ask", "--question", case["question"], "--as-of", case["as_of"])
        if not isinstance(outcome, dict):
            raise PublicFailure("malformed public outcome")
        record["interpretation"] = outcome.get("interpretation")
        record["phase"] = "interpreted"
        retain(dict(record))
        errors = score_intent(case, outcome)
        if errors:
            record.update(outcome="fail", errors=errors)
        elif case["expected"] != "investigate":
            record.update(audit(case, outcome, None))
        else:
            view = outcome["workflow"]
            brief = view["brief"]
            if json.loads(brief["content_json"]) != expected:
                record.update(outcome="fail", errors=["facts"])
            else:
                record["phase"] = "recovery"
                if invoke("recover", "--run-id", view["run_id"]) != outcome:
                    raise PublicFailure("recovery changed exact outcome")
                fields = (
                    "review",
                    "--run-id",
                    view["run_id"],
                    "--brief-id",
                    brief["brief_id"],
                    "--digest",
                    brief["digest"],
                    "--decision",
                    "approve",
                )
                try:
                    invoke(
                        "review",
                        "--run-id",
                        view["run_id"],
                        "--brief-id",
                        brief["brief_id"],
                        "--digest",
                        "0" * 64,
                        "--decision",
                        "approve",
                    )
                except PublicFailure as error:
                    if str(error) != "pil.policy.brief_review_conflict":
                        raise
                else:
                    raise PublicFailure("altered digest accepted")
                record["phase"] = "save"
                retain(dict(record))
                saved = invoke(*fields)
                if saved.get("status") != "completed" or invoke(*fields) != saved:
                    raise PublicFailure("save is not completed/idempotent")
                record.update(audit(case, outcome, saved))
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as error:
        record.update(outcome="unknown", errors=[type(error).__name__])
    except (PublicFailure, KeyError, ValueError, TypeError, RuntimeError) as error:
        record.update(outcome="fail", errors=[str(error)[:200]])
    record["public_roundtrip_seconds"] = time.monotonic() - began
    retain(dict(record))
    return record


@contextmanager
def installed_inspector(python: Path):
    # Existing installed handler on an OS-selected port; no product-code replacement.
    script = (
        "from http.server import ThreadingHTTPServer; "
        "from procurement_intelligence_lab.interfaces.web import InspectorHandler; "
        's=ThreadingHTTPServer(("127.0.0.1",0),InspectorHandler); '
        "print(s.server_port,flush=True); s.serve_forever()"
    )
    process = subprocess.Popen(
        [str(python.absolute()), "-c", script],
        cwd="/tmp",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        if process.stdout is None or not select.select([process.stdout], [], [], 15)[0]:
            raise PublicFailure("installed inspector did not become ready")
        port = int(process.stdout.readline().strip())
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        process.communicate(timeout=10)


def saved_records(database: Path, run_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(database) as db:
        rows = db.execute(
            "SELECT s.payload FROM saved_briefs s JOIN review_briefs b "
            "ON s.brief_id=b.brief_id WHERE b.run_id=?",
            (run_id,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def score_ledger(
    run: AgentRun,
    events: tuple[AgentEvent, ...],
    rows: list[dict[str, Any]],
    saved: dict[str, Any] | None,
) -> dict[str, Any]:
    if saved is None:
        valid = len(events) == 1 and events[0].kind == AgentEventKind.RUN_STARTED and not rows
        trajectory = {
            "outcome": "not_applicable",
            "rationale": "Expected abstention; no graph/tool/save authority exercised.",
        }
        outcome = "pass" if valid else "fail"
    else:
        trajectory = asdict(
            evaluate_trajectory(
                run, events, required_tools=("investigate_quantity", "inspect_source")
            )
        )
        valid = len(rows) == 1 and rows[0]["saved_id"] == saved["saved"]["saved_id"]
        outcome = trajectory["outcome"] if valid else "fail"
    return {
        "outcome": outcome,
        "errors": [] if outcome == "pass" else ["ledger_trajectory_or_save"],
        "model_calls": 1,
        "tool_calls": sum(e.kind == AgentEventKind.TOOL_STARTED for e in events),
        "saved_result_count": len(rows),
        "trajectory": trajectory,
        "run_id": run.run_id,
    }


def audit_attempts(database: Path, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    composition = compose_live(database)
    journal = SqliteInterpretationStore(database)
    rows = []
    for case in cases:
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            case["project"],
            "lab",
            frozenset(Permission),
            "pilot-audit",
        )
        expected_hash = sha256(case["question"].encode()).hexdigest()
        matches = []
        for run in composition.runs.recent(context=context):
            try:
                call = journal.get(run.run_id)
            except RuntimeError:
                continue  # Unknown journal is not a terminal inference attempt.
            if call.question_hash == expected_hash and call.as_of == datetime.fromisoformat(
                case["as_of"]
            ):
                matches.append((run, call))
        if len(matches) != 1:
            rows.append(
                {"id": case["id"], "model_calls": None, "error": "missing_or_duplicate_attempt"}
            )
            continue
        run, call = matches[0]
        require_live_run(run_dto(run), case, call.run_id, asdict(composition.runs.versions))
        events = composition.runs.events(run.run_id, context=context)
        rows.append(
            {
                "id": case["id"],
                "run_id": run.run_id,
                "interpretation": asdict(call),
                "model_calls": None if call.status == "pending" else 1,
                "tool_calls": sum(e.kind == AgentEventKind.TOOL_STARTED for e in events),
                "saved_result_count": len(saved_records(database, run.run_id)),
            }
        )
    ids = [r["run_id"] for r in rows if "run_id" in r]
    if len(ids) != len(set(ids)):
        raise ValueError("independent examples reused a run")
    return rows


def reconcile_attempts(
    cases: list[dict[str, Any]], records: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate audited case")
    by_id = {r["id"]: r for r in rows}
    metadata = {c["id"]: c for c in cases}
    reconciled = []
    complete = len(rows) == len(cases) and len(records) == len(cases)
    seen = set()
    for original in records:
        record = dict(original)
        case = metadata[record["id"]]
        row = by_id.get(record["id"], {})
        call, actual = record.get("interpretation"), row.get("interpretation")
        if (
            row.get("model_calls") != 1
            or not isinstance(call, dict)
            or not isinstance(actual, dict)
        ):
            complete = False
            if record["outcome"] == "pass":
                record.update(outcome="unknown", errors=["missing_terminal_journal"])
        else:
            expected_hash = sha256(case["question"].encode()).hexdigest()
            matches = (
                call.get("run_id") == row.get("run_id") == actual.get("run_id")
                and call.get("question_hash") == actual.get("question_hash") == expected_hash
                and call.get("status") == actual.get("status")
                and call.get("item") == actual.get("item")
                and actual.get("status") != "pending"
                and row.get("run_id") not in seen
            )
            try:
                matches = matches and (
                    datetime.fromisoformat(str(call.get("as_of")))
                    == datetime.fromisoformat(str(actual.get("as_of")))
                    == datetime.fromisoformat(case["as_of"])
                )
            except (ValueError, TypeError):
                matches = False
            seen.add(row.get("run_id"))
            if not matches:
                record.update(
                    outcome="fail", errors=record.get("errors", []) + ["journal_outcome_mismatch"]
                )
                complete = False
            else:
                record["model_calls"] = row["model_calls"]
        reconciled.append(record)
    return reconciled, bool(complete)


def finalize_report(
    report: dict[str, Any], cases: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> None:
    records, complete = reconcile_attempts(cases, report["runs"], rows)
    report["runs"] = records
    report["attempt_audit"] = rows
    report["attempt_audit_complete"] = complete
    report["interpretation"] = summarize(cases, records)
    report["acceptance"] = (
        "bounded_pilot_passed"
        if report["interpretation"]["ready"]
        and report.get("structured", {}).get("ready")
        and complete
        and report.get("save_count_matches")
        and not report.get("operation_errors")
        else "not_ready"
    )


def evaluate_with_baseline(
    case: dict[str, Any],
    fetch: Callable[[], dict[str, Any]],
    invoke: Callable[..., dict[str, Any]],
    audit: Callable[..., dict[str, Any]],
    retain: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    try:
        expected = fetch() if case["expected"] == "investigate" else {}
    except (OSError, TimeoutError, ValueError, TypeError, RuntimeError) as error:
        record = {
            "id": case["id"],
            "outcome": "unknown",
            "errors": ["baseline_" + type(error).__name__],
            "phase": "baseline",
            "model_calls": 0,
        }
        retain(record)
        return record
    return evaluate_case(case, expected, invoke, audit, retain)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true", required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--manifest", type=Path, default=PILOT)
    args = parser.parse_args()
    if args.database.exists() or args.output.exists():
        raise ValueError("fresh database/output required; never overwrite a prior pilot")
    cases = load_pilot(args.dataset, args.manifest)
    frozen = json.loads(args.manifest.read_bytes())
    composition = compose_live(args.database)
    versions = asdict(composition.runs.versions)
    if frozen["schema_version"] in (2, 3):
        from tools.fresh_g2_cohort import validate_fresh

        validate_fresh(args.dataset, args.manifest, versions)
    # Verify the clean artifact rather than relying on its directory name.
    script = (
        "import json,tempfile; from pathlib import Path; from dataclasses import asdict; "
        "from procurement_intelligence_lab.interfaces.live_review import compose_live; "
        'print(json.dumps(asdict(compose_live(Path(tempfile.mkdtemp())/"probe.db").runs.versions)))'
    )
    installed_versions = json.loads(
        subprocess.check_output(
            [str(args.python.absolute()), "-c", script], cwd="/tmp", text=True, timeout=20
        )
    )
    if installed_versions != versions:
        raise ValueError("installed artifact differs from frozen checkout composition")
    report: dict[str, Any] = {
        "schema_version": 1,
        "execution_kind": "live",
        "evaluation_use": frozen["evaluation_use"]
        if frozen["schema_version"] in (2, 3)
        else "development_regression",
        "versions": versions,
        "interpretation_manifest_sha256": sha256(args.manifest.read_bytes()).hexdigest(),
        "dataset_manifest_sha256": sha256(
            (args.dataset / "manifest.json").read_bytes()
        ).hexdigest(),
        "application_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "runs": [],
        "acceptance": "not_ready",
        "limits": "Previously inspected public synthetic cases: development regression, not held-out. Historical project split labels are accounting only; shared generator/query ancestry. No blind/general accuracy, browser/deployment, full adversarial G2 or expansion acceptance. One attempt per case in this run; overlapping development runs are reported separately. Prior results remain immutable.",
    }

    if frozen["schema_version"] in (2, 3):
        report["limits"] = frozen["limits"]
        report["freshness"] = frozen["freshness"]

    def retain() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")

    retain()
    seen: set[str] = set()

    def audit(case, outcome, saved):
        call = outcome["interpretation"]
        run_id = call["run_id"]
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            case["project"],
            "lab",
            frozenset(Permission),
            "pilot-audit",
        )
        run = composition.runs.resume(run_id, context=context)
        require_live_run(run_dto(run), case, run_id, versions)
        if run_id in seen:
            raise ValueError("independent example reused run identity")
        seen.add(run_id)
        events = composition.runs.events(run_id, context=context)
        saved_rows = saved_records(args.database, run_id)
        return score_ledger(run, events, saved_rows, saved) | {
            "model_elapsed_seconds": call["elapsed_seconds"]
        }

    try:
        with urlopen("http://127.0.0.1:8000/version", timeout=5) as response:
            report["server"] = json.load(response)
        with installed_inspector(args.python) as base_url:
            report["structured"] = evaluate(base_url, args.dataset)
            retain()
            if not report["structured"]["ready"]:
                return 1
            for case in cases:

                def fetch(case=case):
                    status, body = _fetch(
                        base_url + "/api/corpus/investigate?" + urlencode(case["request"])
                    )
                    if status != 200:
                        raise PublicFailure("baseline unavailable")
                    return baseline_facts(body)

                def invoke(*fields, case=case):
                    result = subprocess.run(
                        [
                            str(args.python.absolute()),
                            "-m",
                            "procurement_intelligence_lab.interfaces.live_review",
                            "--database",
                            str(args.database.absolute()),
                            "--project",
                            case["project"],
                            *fields,
                        ],
                        cwd="/tmp",
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                    )
                    body = json.loads(result.stdout)
                    if not isinstance(body, dict):
                        raise PublicFailure("malformed public outcome")
                    if result.returncode:
                        raise PublicFailure(body.get("code", "public CLI failed"))
                    return body

                def retain_case(record, case=case):
                    if report["runs"] and report["runs"][-1]["id"] == case["id"]:
                        report["runs"][-1] = record
                    else:
                        report["runs"].append(record)
                    retain()

                record = evaluate_with_baseline(case, fetch, invoke, audit, retain_case)
                print(case["id"], record["outcome"], record["errors"], flush=True)
    except (OSError, TimeoutError, ValueError, TypeError, RuntimeError, AttributeError) as error:
        report["operation_errors"] = [type(error).__name__]
    finally:
        try:
            rows = audit_attempts(args.database, cases)
            with sqlite3.connect(args.database) as db:
                report["durable_saved_results"] = db.execute(
                    "SELECT COUNT(*) FROM saved_briefs"
                ).fetchone()[0]
            expected_saved = sum(r.get("saved_result_count", 0) for r in report["runs"])
            report["save_count_matches"] = report["durable_saved_results"] == expected_saved
        except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error) as error:
            rows = []
            report.setdefault("operation_errors", []).append("audit_" + type(error).__name__)
        finalize_report(report, cases, rows)
        retain()
    return int(report["acceptance"] == "not_ready")


if __name__ == "__main__":
    raise SystemExit(main())
