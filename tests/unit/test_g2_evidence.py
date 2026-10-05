"""A dossier cannot hide missing evidence, inspected misses or incompatible timing."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEvent,
    AgentEventKind,
    AgentRun,
    ExecutionKind,
    RunVersions,
    event_dto,
    run_dto,
)
from tools.g2_evidence import compile_report, timing


def control() -> tuple[dict[str, Any], dict[str, Any]]:
    interpretation = {
        "run_id": "run",
        "question_hash": "hash",
        "as_of": "2026-10-01T00:00:00+00:00",
        "status": "clarify",
        "item": None,
        "reason": "date_ambiguous",
        "elapsed_seconds": 0.25,
        "prompt_tokens": 20,
        "completion_tokens": 4,
    }
    row = {
        "id": "known-miss",
        "outcome": "fail",
        "interpretation": interpretation,
        "errors": ["interpretation_status"],
        "model_calls": 1,
    }
    audited = {
        "id": "known-miss",
        "run_id": "run",
        "interpretation": deepcopy(interpretation),
        "model_calls": 1,
        "tool_calls": 0,
        "saved_result_count": 0,
    }
    return {
        "versions": {"application": "frozen"},
        "evaluation_use": "development",
        "saved_results": 0,
        "runs": [row],
        "attempt_audit": [audited],
        "attempt_audit_complete": True,
    }, {"ids": ["known-miss"], "versions": {"application": "frozen"}}


def test_control_miss_is_retained_with_actual_counts():
    raw, spec = control()
    result = compile_report("candidate_controls", raw, spec)
    assert result["evidence_status"] == "pass"
    assert result["counts"] == {"pass": 0, "fail": 1, "unknown": 0, "not_applicable": 0}
    assert result["real_model_attempts"] == 1
    assert result["tool_starts"] == result["saves"] == 0
    assert result["model_transport_seconds"]["count"] == 1
    assert result["cost_observed_usd"] is None


@pytest.mark.parametrize(
    "damage",
    [
        "omitted",
        "duplicate",
        "foreign",
        "audit_missing",
        "audit_foreign",
        "pending",
        "wrong_version",
    ],
)
def test_missing_or_contradictory_control_evidence_blocks_compilation(damage: str):
    raw, spec = control()
    if damage == "omitted":
        raw["runs"] = []
    elif damage == "duplicate":
        raw["runs"].append(deepcopy(raw["runs"][0]))
    elif damage == "foreign":
        raw["runs"][0]["id"] = "foreign"
    elif damage == "audit_missing":
        raw["attempt_audit"] = []
    elif damage == "audit_foreign":
        raw["attempt_audit"][0]["interpretation"]["run_id"] = "foreign"
    elif damage == "pending":
        raw["attempt_audit"][0]["interpretation"]["status"] = "pending"
    else:
        raw["versions"]["application"] = "other"
    result = compile_report("candidate_controls", raw, spec)
    assert result["evidence_status"] != "pass", result
    if damage in ("audit_missing", "pending"):
        assert result["real_model_attempts"] is None


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf"), True])
def test_invalid_timing_is_not_a_measured_latency(value: float):
    with pytest.raises(ValueError):
        timing([value])


def test_unknown_timing_is_not_zero_and_zero_is_valid():
    assert timing([None]) == {
        "count": 0,
        "unknown": 1,
        "min": None,
        "median": None,
        "p95": None,
        "max": None,
    }
    assert timing([0.0, 1.0])["median"] == 0.5


def test_missing_factual_completion_cannot_be_promoted_by_aggregate_flag():
    raw, spec = control()
    raw["runs"][0].update(
        outcome="pass",
        phase="save",
        tool_calls=2,
        saved_result_count=1,
        trajectory={"outcome": "unknown"},
    )
    raw.update(
        execution_kind="live",
        acceptance="bounded_pilot_passed",
        save_count_matches=True,
        durable_saved_results=1,
        structured={
            "results": [{"id": "known-miss", "outcome": "pass"}],
            "source_references_resolved": 1,
        },
    )
    result = compile_report("fresh_language", raw, spec | {"source_checks": 1})
    assert result["evidence_status"] != "pass"


def test_invalid_latency_keeps_known_terminal_attempts():
    raw, spec = control()
    raw["attempt_audit"][0]["interpretation"]["elapsed_seconds"] = -1
    result = compile_report("candidate_controls", raw, spec)
    assert result["evidence_status"] == "fail"
    assert result["real_model_attempts"] == 1


def test_valid_completed_fresh_row_and_baseline_agree():
    raw, spec = control()
    raw["runs"][0]["interpretation"].update(status="investigate", item="GPU-A", reason="none")
    raw["attempt_audit"][0].update(
        interpretation=deepcopy(raw["runs"][0]["interpretation"]),
        tool_calls=2,
        saved_result_count=1,
    )
    raw["runs"][0].update(
        outcome="pass",
        phase="save",
        tool_calls=2,
        saved_result_count=1,
        trajectory={"outcome": "pass", "run_id": "run", "tool_calls": 2, "execution_kind": "live"},
    )
    raw.update(
        execution_kind="live",
        save_count_matches=True,
        durable_saved_results=1,
        structured={
            "results": [{"id": "known-miss", "outcome": "pass"}],
            "source_references_resolved": 1,
        },
    )
    result = compile_report("fresh_language", raw, spec | {"source_checks": 1})
    assert result["evidence_status"] == "pass", result
    raw["runs"][0]["trajectory"] = {"outcome": "unknown"}
    result = compile_report("fresh_language", raw, spec | {"source_checks": 1})
    assert result["evidence_status"] == "unknown", result
    assert result["real_model_attempts"] == 1


def original() -> tuple[dict[str, Any], dict[str, Any]]:
    sources = ("showcase-a-order", "showcase-a-b-order", "showcase-a-only")
    versions = {
        source: {
            "provider": "local",
            "model": "qwen",
            "prompt": "fixed",
            "application": "frozen",
            "fixture": "original:" + source,
            "tool_schema": "corpus-tools/v1",
        }
        for source in sources
    }
    raw: dict[str, Any] = {
        "execution_kind": "live",
        "runs": [],
        "ledgers": {},
        "versions": versions,
    }
    spec: dict[str, Any] = {"ids": [], "versions": versions, "scenarios": {}}
    for source in sources:
        ledger: dict[str, Any] = {"runs": [], "events": [], "calls": [], "saves": []}
        spec["scenarios"][source] = {
            "required_quantity": "4",
            "ordered_quantity": "2",
            "status": "anomaly",
            "reason": None,
            "evidence_ids": [source],
        }
        for repetition in (1, 2, 3):
            identity = f"{source}:{repetition}"
            created = datetime(2026, 10, 1, tzinfo=UTC)
            run = AgentRun(
                identity,
                "q-" + identity,
                "a-" + identity,
                "t-" + identity,
                "local-demo",
                "synthetic-tenant",
                "synthetic-project",
                "synthetic-site",
                created,
                ExecutionKind.LIVE,
                RunVersions(**versions[source]),
            )
            events: list[dict[str, object]] = []
            for i, (kind, tool, snapshot) in enumerate(
                [
                    ("run_started", None, None),
                    ("tool_started", "investigate_quantity", None),
                    ("tool_succeeded", "investigate_quantity", "snapshot"),
                    ("tool_started", "inspect_source", None),
                    ("tool_succeeded", "inspect_source", "source"),
                    ("run_completed", None, None),
                ]
            ):
                event = AgentEvent(
                    f"e{i}-" + identity,
                    run.run_id,
                    run.query_id,
                    run.attempt_id,
                    created + timedelta(seconds=i),
                    AgentEventKind(kind),
                    f"e{i - 1}-" + identity if i else None,
                    tool,
                    "corpus-tools/v1" if tool else None,
                    snapshot,
                )
                events.append(event_dto(event))
            call = {
                "run_id": identity,
                "question_hash": "hash",
                "as_of": created.isoformat(),
                "status": "investigate",
                "item": "GPU-A",
                "reason": "none",
                "elapsed_seconds": 0.25,
                "prompt_tokens": 20,
                "completion_tokens": 4,
            }
            reject = source == "showcase-a-b-order" and repetition == 1
            row: dict[str, Any] = {
                "sources": source,
                "repetition": repetition,
                "run_id": identity,
                "outcome": "pass",
                "interpretation": call,
                "source_count": 1,
                "process_restart_recovered": repetition == 1,
                "decision": "reject" if reject else "approve",
                "digest": "digest-" + identity,
                "saved_id": None if reject else "saved-" + identity,
                "facts": spec["scenarios"][source] | {"evidence": [{"evidence_id": source}]},
            }
            raw["runs"].append(row)
            spec["ids"].append(identity)
            ledger["runs"].append(run_dto(run))
            ledger["calls"].append(call)
            ledger["events"].extend(events)
            if not reject:
                ledger["saves"].append(
                    {
                        "run_id": identity,
                        "saved_id": row["saved_id"],
                        "digest": row["digest"],
                        "idempotency_key": "brief-save:" + row["digest"],
                    }
                )
        raw["ledgers"][source] = ledger
    return raw, spec


def test_completed_rejection_is_terminal_without_a_save():
    raw, spec = original()
    result = compile_report("original_browser", raw, spec)
    assert result["evidence_status"] == "pass", result
    assert result["real_model_attempts"] == 9
    assert result["saves"] == 8


def test_missing_original_result_is_unknown_not_a_success():
    raw, spec = original()
    raw["ledgers"]["showcase-a-order"]["events"].pop(2)
    result = compile_report("original_browser", raw, spec)
    assert result["evidence_status"] == "unknown", result
    assert result["real_model_attempts"] == 9


@pytest.mark.parametrize(
    "damage", ["orphan_save", "reused_trial", "extra_run", "saved_identity", "idempotency"]
)
def test_original_ledger_is_a_closed_one_to_one_population(damage: str):
    raw, spec = original()
    ledger = raw["ledgers"]["showcase-a-order"]
    if damage == "orphan_save":
        ledger["saves"].append(ledger["saves"][0] | {"run_id": "foreign", "saved_id": "foreign"})
    elif damage == "reused_trial":
        raw["runs"][1] = deepcopy(raw["runs"][0]) | {
            "repetition": 2,
            "process_restart_recovered": False,
        }
    elif damage == "extra_run":
        ledger["runs"].append(ledger["runs"][0] | {"run_id": "foreign"})
    elif damage == "saved_identity":
        ledger["saves"][1]["saved_id"] = ledger["saves"][0]["saved_id"]
        raw["runs"][1]["saved_id"] = raw["runs"][0]["saved_id"]
    else:
        ledger["saves"][1]["idempotency_key"] = ledger["saves"][0]["idempotency_key"]
    result = compile_report("original_browser", raw, spec)
    assert result["evidence_status"] == "fail", result


def test_original_foreign_tool_version_is_a_contradiction():
    raw, spec = original()
    for ledger in raw["ledgers"].values():
        for event in ledger["events"]:
            if event["tool_name"]:
                event["tool_version"] = "foreign"
    assert compile_report("original_browser", raw, spec)["evidence_status"] == "fail"


@pytest.mark.parametrize("role", ["baseline_controls", "candidate_controls"])
@pytest.mark.parametrize("damage", ["disagrees", "missing", "negative", "boolean"])
def test_control_durable_save_total_must_agree(role: str, damage: str):
    raw, spec = control()
    if damage == "missing":
        raw.pop("saved_results")
    else:
        raw["saved_results"] = {"disagrees": 2, "negative": -1, "boolean": False}[damage]
    result = compile_report(role, raw, spec)
    assert result["evidence_status"] == ("unknown" if damage == "missing" else "fail"), result
    assert result["real_model_attempts"] == 1


def deterministic() -> tuple[dict[str, Any], dict[str, Any]]:
    ids = ["accepted", "expected-rejection"]
    versions = {"application": "fixed"}
    raw = {
        "versions": versions,
        "structured": {
            "results": [{"id": i, "outcome": "pass"} for i in ids],
            "source_references_resolved": 1,
        },
        "investigation_requests": [
            {"id": ids[0], "status": 200, "seconds": 0.1},
            {"id": ids[1], "status": 422, "seconds": 0.01},
        ],
        "source_requests": [{"status": 200, "seconds": 0.1}],
    }
    return raw, {
        "ids": ids,
        "versions": versions,
        "source_checks": 1,
        "http_statuses": {"accepted": 200, "expected-rejection": 422},
    }


@pytest.mark.parametrize("status", [500, 200, None])
def test_baseline_observed_status_must_match_pinned_oracle(status: int | None):
    raw, spec = deterministic()
    raw["investigation_requests"][1]["status"] = status
    result = compile_report("deterministic_baseline", raw, spec)
    assert result["evidence_status"] == ("unknown" if status is None else "fail"), result


def test_expected_http_rejection_is_a_valid_baseline_observation():
    raw, spec = deterministic()
    assert compile_report("deterministic_baseline", raw, spec)["evidence_status"] == "pass"


def test_original_replayed_telemetry_is_not_another_tool_invocation():
    raw, spec = original()
    ledger = raw["ledgers"]["showcase-a-order"]
    ledger["events"].append(deepcopy(ledger["events"][1]))
    result = compile_report("original_browser", raw, spec)
    assert result["evidence_status"] == "pass", result
    assert result["tool_starts"] == 18
    assert result["saves"] == 8
