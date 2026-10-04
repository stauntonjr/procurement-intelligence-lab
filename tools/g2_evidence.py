"""Compile pinned historical evidence; never pool quality populations or grant authority."""

import json
import math
import statistics
from collections import Counter
from datetime import datetime
from typing import Any

from procurement_intelligence_lab.adapters.sqlite_agent_runs import decode_run
from procurement_intelligence_lab.application.agent_trajectory import evaluate_trajectory
from procurement_intelligence_lab.platform.semantics.agent_runs import AgentEvent, AgentEventKind
from tools.run_g2_adversarial import CASES, audit_evidence, summarize

ROLES = (
    "fresh_language",
    "original_browser",
    "adversarial",
    "baseline_controls",
    "candidate_controls",
    "deterministic_baseline",
)
REQUIRED_SUITE = ("fresh_language", "original_browser", "adversarial", "deterministic_baseline")


class MissingEvidence(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def inventory(rows: list[dict[str, Any]], ids: list[str]) -> dict[str, dict[str, Any]]:
    by_id = {row["id"]: row for row in rows}
    require(len(by_id) == len(rows) and not set(by_id) - set(ids), "duplicate_or_foreign_rows")
    if set(ids) - set(by_id):
        raise MissingEvidence("missing_rows")
    return by_id


def timing(values: list[Any]) -> dict[str, Any]:
    observed = [v for v in values if v is not None]
    require(
        all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in observed),
        "invalid_timing",
    )
    ordered = sorted(observed)
    return {
        "count": len(ordered),
        "unknown": len(values) - len(ordered),
        "min": ordered[0] if ordered else None,
        "median": statistics.median(ordered) if ordered else None,
        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else None,
        "max": ordered[-1] if ordered else None,
    }


def _outcomes(rows: list[dict[str, Any]], ids: list[str]) -> dict[str, int]:
    counts = Counter(row.get("outcome", "unknown") for row in rows)
    require(not set(counts) - {"pass", "fail", "unknown", "not_applicable"}, "invalid_outcome")
    counts["unknown"] += len(set(ids) - {row["id"] for row in rows})
    return {name: counts[name] for name in ("pass", "fail", "unknown", "not_applicable")}


def _calls(
    role: str, raw: dict[str, Any], ids: list[str]
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Only observed terminal journals contribute to model metrics."""
    if role == "original_browser":
        ledgers = raw["ledgers"].values()
        calls = [c for ledger in ledgers for c in ledger["calls"]]
        tools = sum(
            e["kind"] == "tool_started"
            for ledger in raw["ledgers"].values()
            for e in ledger["events"]
        )
        saves = sum(len(ledger["saves"]) for ledger in raw["ledgers"].values())
    else:
        audited = inventory(raw["attempt_audit"], ids)
        if not raw.get("attempt_audit_complete"):
            raise MissingEvidence("incomplete_attempt_audit")
        calls = [r["interpretation"] for r in audited.values()]
        require(
            all(
                type(r["model_calls"]) is int
                and r["model_calls"] == 1
                and type(r["tool_calls"]) is int
                and r["tool_calls"] >= 0
                and type(r["saved_result_count"]) is int
                and r["saved_result_count"] >= 0
                for r in audited.values()
            ),
            "invalid_attempt_counts",
        )
        tools = sum(r["tool_calls"] for r in audited.values())
        saves = sum(r["saved_result_count"] for r in audited.values())
    if any(c["status"] == "pending" for c in calls) or len(calls) != len(ids):
        raise MissingEvidence("missing_terminal_attempts")
    require(len({c["run_id"] for c in calls}) == len(calls), "duplicate_attempt")
    return calls, len(calls), tools, saves


def _interpretation_equal(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first, second = dict(first), dict(second)
    first["as_of"] = datetime.fromisoformat(first["as_of"])
    second["as_of"] = datetime.fromisoformat(second["as_of"])
    return first == second


def call_observations(calls: list[dict[str, Any]]) -> dict[str, Any]:
    usage: dict[str, Any] = {}
    for field in ("prompt_tokens", "completion_tokens"):
        values = [c.get(field) for c in calls]
        require(
            all(v is None or (type(v) is int and v >= 0) for v in values), "invalid_token_usage"
        )
        usage[field] = {
            "total": sum(v for v in values if v is not None)
            if all(v is not None for v in values)
            else None,
            "observed_calls": sum(v is not None for v in values),
            "unknown_calls": sum(v is None for v in values),
        }
    return {
        "model_status_counts": dict(Counter(c["status"] for c in calls)),
        "reported_token_usage": usage,
    }


def _fresh_or_control(role: str, raw: dict[str, Any], spec: dict[str, Any]) -> None:
    rows = inventory(raw["runs"], spec["ids"])
    audits = inventory(raw["attempt_audit"], spec["ids"])
    for key, row in rows.items():
        audit = audits[key]
        require(
            row["model_calls"] == audit["model_calls"] == 1
            and row["interpretation"]["run_id"] == audit["run_id"]
            and _interpretation_equal(row["interpretation"], audit["interpretation"]),
            "score_journal_disagreement",
        )
        if role != "fresh_language":
            continue
        require(raw["execution_kind"] == "live", "not_live")
        for field, source in (
            ("tool_calls", "tool_calls"),
            ("saved_result_count", "saved_result_count"),
        ):
            require(row[field] == audit[source], "workflow_count_disagreement")
        if row["interpretation"]["status"] == "investigate":
            if row["trajectory"]["outcome"] == "unknown":
                raise MissingEvidence("missing_completed_trajectory")
            require(
                row["trajectory"]["outcome"] == "pass"
                and row["trajectory"]["run_id"] == audit["run_id"]
                and row["trajectory"]["execution_kind"] == "live"
                and row["tool_calls"] == row["trajectory"]["tool_calls"] == 2
                and row["saved_result_count"] == 1,
                "invalid_completed_trajectory",
            )
        else:
            require(
                row["tool_calls"] == row["saved_result_count"] == 0
                and row["trajectory"]["outcome"] == "not_applicable",
                "abstention_did_work",
            )
    if role == "fresh_language":
        structured = inventory(raw["structured"]["results"], spec["ids"])
        require(
            all(r["outcome"] == "pass" for r in structured.values())
            and raw["structured"]["source_references_resolved"] == spec["source_checks"]
            and raw["save_count_matches"] is True
            and raw["durable_saved_results"] == sum(r["saved_result_count"] for r in rows.values()),
            "baseline_or_save_disagreement",
        )


def _original(raw: dict[str, Any], spec: dict[str, Any]) -> None:
    rows = inventory(
        [r | {"id": f"{r['sources']}:{r['repetition']}"} for r in raw["runs"]], spec["ids"]
    )
    require(
        raw["execution_kind"] == "live" and set(raw["ledgers"]) == set(spec["scenarios"]),
        "foreign_original_scope",
    )
    for row in rows.values():
        source = row["sources"]
        expected = spec["scenarios"][source]
        ledger = raw["ledgers"][source]
        run_id = row["run_id"]
        matching = [r for r in ledger["runs"] if r["run_id"] == run_id]
        if len(matching) != 1:
            raise MissingEvidence("missing_original_run")
        run = decode_run(json.dumps(matching[0]))
        require(
            matching[0]["versions"] == spec["versions"][source]
            and run.execution_kind.value == "live"
            and (run.principal_id, run.tenant_id, run.project_id, run.site_id)
            == ("local-demo", "synthetic-tenant", "synthetic-project", "synthetic-site"),
            "foreign_original_binding",
        )
        calls = [c for c in ledger["calls"] if c["run_id"] == run_id]
        require(
            len(calls) == 1 and _interpretation_equal(calls[0], row["interpretation"]),
            "original_call_disagreement",
        )
        facts = row["facts"]
        require(
            all(
                facts[k] == expected[k]
                for k in ("required_quantity", "ordered_quantity", "status", "reason")
            )
            and sorted(e["evidence_id"] for e in facts["evidence"])
            == sorted(expected["evidence_ids"])
            and row["source_count"] == len(expected["evidence_ids"]),
            "original_facts_or_sources",
        )
        events = tuple(
            AgentEvent(
                **(
                    e
                    | {
                        "kind": AgentEventKind(e["kind"]),
                        "occurred_at": datetime.fromisoformat(e["occurred_at"]),
                    }
                )
            )
            for e in ledger["events"]
            if e["run_id"] == run_id
        )
        unique = {e.event_id: e for e in events}
        require(all(unique[e.event_id] == e for e in events), "conflicting_original_event")
        require(
            all(
                (e.run_id, e.query_id, e.attempt_id) == (run.run_id, run.query_id, run.attempt_id)
                for e in events
            ),
            "foreign_original_event",
        )
        actual = Counter((e.kind.value, e.tool_name) for e in unique.values())
        required = Counter(
            [
                ("run_started", None),
                ("tool_started", "investigate_quantity"),
                ("tool_succeeded", "investigate_quantity"),
                ("tool_started", "inspect_source"),
                ("tool_succeeded", "inspect_source"),
                ("run_completed", None),
            ]
        )
        require(not actual - required, "unexpected_original_event")
        if required - actual or any(
            e.parent_id not in unique for e in events if e.kind != AgentEventKind.RUN_STARTED
        ):
            raise MissingEvidence("partial_original_trajectory")
        trajectory = evaluate_trajectory(
            run, events, required_tools=("investigate_quantity", "inspect_source")
        )
        if trajectory.outcome == "unknown":
            raise MissingEvidence("partial_original_trajectory")
        require(
            trajectory.outcome == "pass" and trajectory.tool_calls == 2,
            "invalid_original_trajectory",
        )
        saved = [s for s in ledger["saves"] if s["run_id"] == run_id]
        require(len(saved) == int(row["decision"] == "approve"), "duplicate_or_unapproved_save")
        if saved:
            require(
                saved[0]["saved_id"] == row["saved_id"] and saved[0]["digest"] == row["digest"],
                "saved_identity_disagreement",
            )
    require(
        sum(bool(r.get("process_restart_recovered")) for r in rows.values()) == 3,
        "missing_three_process_recoveries",
    )
    require(
        all(
            e["run_id"] in {r["run_id"] for r in ledger["runs"]}
            for ledger in raw["ledgers"].values()
            for e in ledger["events"]
        ),
        "orphan_original_event",
    )


def compile_report(role: str, raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "evidence_status": "unknown",
        "errors": [],
        "counts": None,
        "real_model_attempts": None,
        "controlled_protocol_attempts": None,
        "tool_starts": None,
        "saves": None,
        "model_transport_seconds": timing([]),
        "cost_observed_usd": None,
    }
    try:
        require(role in ROLES, "foreign_role")
        if role == "adversarial":
            rows = inventory(raw["records"], spec["ids"])
            result["counts"] = summarize(list(rows.values()))["counts"]
            real_calls: list[dict[str, Any]] = []
            controlled = tools = saves = failed = 0
            controlled_calls: list[dict[str, Any]] = []
            for name, row in rows.items():
                require(row["kind"] == CASES[name], "wrong_provider_population")
                journal = row["journal"]
                evidence = audit_evidence(name, journal, row["observations"], row["versions"])
                if evidence["outcome"] == "unknown":
                    raise MissingEvidence("missing_adversarial_evidence")
                require(evidence["outcome"] == "pass", "contradictory_adversarial_evidence")
                calls = journal["calls"]
                if len(calls) != (0 if name == "request_guards" else 1) or any(
                    c["status"] == "pending" for c in calls
                ):
                    raise MissingEvidence("missing_adversarial_attempts")
                if row["kind"] == "real_qwen":
                    require(row["versions"] == spec["versions"], "wrong_runtime_version")
                    real_calls.extend(calls)
                else:
                    require(
                        all(
                            row["versions"][k] == v
                            for k, v in spec["versions"].items()
                            if k != "prompt"
                        ),
                        "wrong_controlled_runtime",
                    )
                    controlled += len(calls)
                    controlled_calls.extend(calls)
                tools += sum(e["kind"] == "tool_started" for e in journal["events"])
                failed += sum(e["kind"] == "tool_failed" for e in journal["events"])
                saves += len(journal["saved"])
            result.update(
                real_model_attempts=len(real_calls),
                controlled_protocol_attempts=controlled,
                tool_starts=tools,
                tool_failures=failed,
                saves=saves,
                model_transport_seconds=timing([c.get("elapsed_seconds") for c in real_calls]),
            )
            result.update(call_observations(real_calls))
            result["controlled_model_status_counts"] = dict(
                Counter(c["status"] for c in controlled_calls)
            )
            require(summarize(list(rows.values()))["ready"], "adversarial_not_ready")
        elif role == "deterministic_baseline":
            require(raw["versions"] == spec["versions"], "wrong_runtime_version")
            rows = inventory(raw["structured"]["results"], spec["ids"])
            measured = inventory(raw["investigation_requests"], spec["ids"])
            result.update(
                counts=_outcomes(list(rows.values()), spec["ids"]),
                real_model_attempts=0,
                controlled_protocol_attempts=0,
                tool_starts=0,
                saves=0,
                investigation_http_seconds=timing([r.get("seconds") for r in measured.values()]),
                source_http_seconds=timing([r.get("seconds") for r in raw["source_requests"]]),
            )
            require(
                raw["structured"]["source_references_resolved"] == spec["source_checks"]
                and len(raw["source_requests"]) == spec["source_checks"]
                and all(r["status"] == 200 for r in raw["source_requests"]),
                "baseline_source_inventory",
            )
        else:
            calls, count, tools, saves = _calls(role, raw, spec["ids"])
            result.update(
                real_model_attempts=count,
                controlled_protocol_attempts=0,
                tool_starts=tools,
                saves=saves,
            )
            result["model_transport_seconds"] = timing([c.get("elapsed_seconds") for c in calls])
            result.update(call_observations(calls))
            require(raw["versions"] == spec["versions"], "wrong_runtime_version")
            if role == "original_browser":
                _original(raw, spec)
                rows = [r | {"id": f"{r['sources']}:{r['repetition']}"} for r in raw["runs"]]
            else:
                _fresh_or_control(role, raw, spec)
                rows = raw["runs"]
            result["counts"] = _outcomes(rows, spec["ids"])
            result["failed_cases"] = [
                {
                    "id": r["id"],
                    "errors": r.get("errors", []),
                    "status": r["interpretation"]["status"],
                    "reason": r["interpretation"]["reason"],
                }
                for r in rows
                if r["outcome"] == "fail"
            ]
            if role == "fresh_language":
                result["public_workflow_roundtrip_seconds"] = timing(
                    [r.get("public_roundtrip_seconds") for r in rows]
                )
        result["evidence_status"] = "pass"
    except MissingEvidence as error:
        result["errors"].append(str(error))
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, RuntimeError) as error:
        result.update(
            evidence_status="fail",
            errors=[str(error) if type(error) is ValueError else type(error).__name__],
        )
    return result
