"""Runner failure records must survive partial public calls."""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools.run_g2_pilot import baseline_facts, evaluate_case, require_live_run


def case() -> dict[str, Any]:
    return {
        "id": "q",
        "project": "atlas",
        "question": "Compare GPU-A.",
        "item": "GPU-A",
        "as_of": "2026-10-01T00:00:00+00:00",
        "expected": "investigate",
        "category": "exact_identifier",
        "split": "development",
    }


def test_timeout_retained_without_retry() -> None:
    calls: list[tuple[str, ...]] = []
    retained: list[dict[str, Any]] = []

    def invoke(*args: str) -> dict[str, Any]:
        calls.append(args)
        raise subprocess.TimeoutExpired("public CLI", 60)

    result = evaluate_case(case(), {}, invoke, lambda *_: {}, retained.append)
    assert len(calls) == 1
    assert result["outcome"] == "unknown"
    assert result["model_calls"] is None
    assert retained and retained[-1]["outcome"] == "unknown"


def test_wrong_source_baseline_cannot_be_approved() -> None:
    retained: list[dict[str, Any]] = []
    value = {
        "interpretation": {
            "status": "investigate",
            "item": "GPU-A",
            "as_of": case()["as_of"],
            "run_id": "r",
        },
        "workflow": {
            "run_id": "r",
            "execution_kind": "live",
            "brief": {"run": {"project_id": "atlas"}, "content_json": '{"quantity":4}'},
        },
    }
    calls: list[tuple[str, ...]] = []

    def invoke(*args: str) -> dict[str, Any]:
        calls.append(args)
        return value

    result = evaluate_case(case(), {"quantity": 5}, invoke, lambda *_: {}, retained.append)
    assert result["outcome"] == "fail"
    assert "facts" in result["errors"]
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["fixture", "foreign", "versions", "identity"])
def test_run_binding_rejected(mutation: str) -> None:
    run: dict[str, Any] = {
        "execution_kind": "live",
        "project_id": "atlas",
        "principal_id": "local-demo",
        "tenant_id": "synthetic-tenant",
        "site_id": "lab",
        "versions": {"v": "one"},
        "run_id": "r",
    }
    if mutation == "fixture":
        run["execution_kind"] = "fixture"
    if mutation == "foreign":
        run["project_id"] = "delta"
    if mutation == "versions":
        run["versions"] = {"v": "other"}
    if mutation == "identity":
        run["run_id"] = "other"
    with pytest.raises(ValueError):
        require_live_run(run, case(), "r", {"v": "one"})


def test_baseline_urls_removed_without_losing_locator() -> None:
    assert baseline_facts(
        {
            "project": "atlas",
            "evidence": [{"evidence_id": "e", "url": "/source", "row": 2}],
            "quantity": "4",
        }
    ) == {"evidence": [{"evidence_id": "e", "row": 2}], "quantity": "4"}


def test_partial_trajectory_is_unknown_not_pass_or_fail(tmp_path: Path) -> None:
    from procurement_intelligence_lab.adapters.sqlite_agent_runs import SqliteRunStore
    from procurement_intelligence_lab.application.agent_runs import AgentRunService
    from procurement_intelligence_lab.platform.semantics.agent_runs import (
        ExecutionKind,
        RunVersions,
    )
    from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
    from tools.run_g2_pilot import score_ledger

    context = RequestContext(
        "local-demo", "synthetic-tenant", "atlas", "lab", frozenset(Permission), "test"
    )
    app = AgentRunService(
        SqliteRunStore(Path(tmp_path) / "r.db"),
        versions=RunVersions("local", "m", "p", "t", "f", "a"),
        execution_kind=ExecutionKind.LIVE,
    )
    run = app.start(context=context)
    saved = {"saved": {"saved_id": "s"}}
    result = score_ledger(run, app.events(run.run_id, context=context), [{"saved_id": "s"}], saved)
    assert result["outcome"] == "unknown"
    assert result["trajectory"]["outcome"] == "unknown"
    assert (
        score_ledger(run, app.events(run.run_id, context=context), [], saved)["outcome"] == "fail"
    )


def test_ledger_audit_retains_pending_as_unknown(tmp_path: Path) -> None:
    from datetime import datetime
    from hashlib import sha256

    from procurement_intelligence_lab.adapters.sqlite_interpretation import (
        SqliteInterpretationStore,
    )
    from procurement_intelligence_lab.interfaces.live_review import compose_live
    from procurement_intelligence_lab.platform.semantics.interpretation import InterpretationCall
    from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
    from tools.run_g2_pilot import audit_attempts

    database = tmp_path / "audit.db"
    composition = compose_live(database)
    context = RequestContext(
        "local-demo", "synthetic-tenant", "atlas", "lab", frozenset(Permission), "test"
    )
    run = composition.runs.start(context=context)
    query = case()
    SqliteInterpretationStore(database).create(
        InterpretationCall(
            run.run_id,
            sha256(query["question"].encode()).hexdigest(),
            datetime.fromisoformat(query["as_of"]),
        )
    )
    result = audit_attempts(database, [query])
    assert result[0]["model_calls"] is None
    assert result[0]["interpretation"]["status"] == "pending"
    assert result[0]["tool_calls"] == 0
    assert result[0]["saved_result_count"] == 0


def test_missing_or_pending_attempt_blocks_acceptance() -> None:
    from hashlib import sha256

    from tools.run_g2_pilot import reconcile_attempts

    call = {
        "run_id": "r",
        "question_hash": sha256(case()["question"].encode()).hexdigest(),
        "as_of": case()["as_of"],
        "status": "investigate",
        "item": "GPU-A",
    }
    record: dict[str, Any] = {"id": "q", "outcome": "pass", "errors": [], "interpretation": call}
    row: dict[str, Any] = {"id": "q", "run_id": "r", "model_calls": 1, "interpretation": call}
    assert reconcile_attempts([case()], [record], [row])[1]
    assert not reconcile_attempts([case()], [record], [row | {"model_calls": None}])[1]
    assert reconcile_attempts([case()], [record], [])[0][0]["outcome"] == "unknown"
    with pytest.raises(ValueError):
        reconcile_attempts([case()], [record], [row, row])


@pytest.mark.parametrize("body", [None, [], {"interpretation": {}, "workflow": []}])
def test_non_object_public_outcome_retained(body: Any) -> None:
    retained: list[dict[str, Any]] = []
    result = evaluate_case(case(), {}, lambda *_: body, lambda *_: {}, retained.append)
    assert result["outcome"] == "fail"
    assert result["errors"] and retained[-1]["errors"]


@pytest.mark.parametrize("mutation", ["run_id", "question_hash", "as_of", "status", "item"])
def test_audit_disagreement_blocks_scored_pass(mutation: str) -> None:
    from copy import deepcopy
    from hashlib import sha256

    from tools.run_g2_pilot import reconcile_attempts

    query = case()
    call = {
        "run_id": "r",
        "question_hash": sha256(query["question"].encode()).hexdigest(),
        "as_of": query["as_of"],
        "status": "investigate",
        "item": query["item"],
    }
    record: dict[str, Any] = {"id": "q", "outcome": "pass", "errors": [], "interpretation": call}
    row: dict[str, Any] = {
        "id": "q",
        "run_id": "r",
        "model_calls": 1,
        "interpretation": deepcopy(call),
    }
    row["interpretation"][mutation] = "wrong"
    records, complete = reconcile_attempts([query], [record], [row])
    assert not complete and records[0]["outcome"] == "fail"


def test_missing_journal_and_baseline_timeout_are_unknown(tmp_path: Path) -> None:
    from procurement_intelligence_lab.interfaces.live_review import compose_live
    from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
    from tools.run_g2_pilot import audit_attempts, evaluate_with_baseline, finalize_report

    database = tmp_path / "missing.db"
    context = RequestContext(
        "local-demo", "synthetic-tenant", "atlas", "lab", frozenset(Permission), "test"
    )
    compose_live(database).runs.start(context=context)
    rows = audit_attempts(database, [case()])
    assert rows[0]["model_calls"] is None and rows[0]["error"]
    retained: list[dict[str, Any]] = []
    calls: list[str] = []

    def fetch() -> dict[str, Any]:
        raise TimeoutError("baseline timeout")

    def invoke(*_: str) -> dict[str, Any]:
        calls.append("called")
        return {}

    result = evaluate_with_baseline(case(), fetch, invoke, lambda *_: {}, retained.append)
    assert result["outcome"] == "unknown" and not calls
    report: dict[str, Any] = {"runs": []}
    finalize_report(report, [case()], rows)
    assert report["interpretation"]["counts"]["unknown"] == 1
    assert report["acceptance"] == "not_ready"
