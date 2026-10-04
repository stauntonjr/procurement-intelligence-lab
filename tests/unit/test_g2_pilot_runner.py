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
