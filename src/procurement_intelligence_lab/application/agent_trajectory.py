"""Score recorded invocation outcomes; fixture traces cannot enter live aggregates."""

from collections import Counter
from dataclasses import dataclass

from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEvent,
    AgentEventKind,
    AgentRun,
    ExecutionKind,
    RunConflict,
    validate_event,
)


@dataclass(frozen=True)
class TrajectoryResult:
    run_id: str
    execution_kind: ExecutionKind
    outcome: str
    errors: tuple[str, ...]
    tool_calls: int
    elapsed_seconds: float | None


def evaluate_trajectory(
    run: AgentRun,
    events: tuple[AgentEvent, ...],
    *,
    required_tools: tuple[str, ...],
    non_applicable_reason: str | None = None,
) -> TrajectoryResult:
    if non_applicable_reason is not None:
        if not non_applicable_reason.strip():
            raise ValueError("non-applicability requires rationale")
        return TrajectoryResult(
            run.run_id, run.execution_kind, "not_applicable", (non_applicable_reason,), 0, None
        )
    unique: dict[str, AgentEvent] = {}
    errors: list[str] = []
    missing: list[str] = []
    for event in events:
        previous = unique.get(event.event_id)
        if previous is not None:
            if previous != event:
                errors.append("conflicting_replay")
            continue
        if (event.run_id, event.query_id, event.attempt_id) != (
            run.run_id,
            run.query_id,
            run.attempt_id,
        ):
            errors.append("foreign_event")
            continue
        if event.kind != AgentEventKind.RUN_STARTED and event.parent_id not in unique:
            missing.append("missing_parent")
        else:
            try:
                validate_event(run, tuple(unique.values()), event)
            except RunConflict:
                errors.append("invalid_lifecycle")
        unique[event.event_id] = event
    ordered = tuple(unique.values())
    if not ordered or ordered[0].kind != AgentEventKind.RUN_STARTED:
        missing.append("missing_run_start")
    if not any(e.kind == AgentEventKind.RUN_COMPLETED for e in ordered):
        missing.append("missing_run_completion")
    if any(e.kind == AgentEventKind.TOOL_FAILED for e in ordered):
        errors.append("tool_failure")
    successful = {e.tool_name for e in ordered if e.kind == AgentEventKind.TOOL_SUCCEEDED}
    if not required_tools or any(tool not in successful for tool in required_tools):
        missing.append("missing_successful_tool")
    outcome = "fail" if errors else "unknown" if missing else "pass"
    elapsed = (ordered[-1].occurred_at - run.created_at).total_seconds() if ordered else None
    return TrajectoryResult(
        run.run_id,
        run.execution_kind,
        outcome,
        tuple(errors + missing),
        sum(e.kind == AgentEventKind.TOOL_STARTED for e in ordered),
        elapsed,
    )


def summarize_trajectories(results: tuple[TrajectoryResult, ...]) -> dict[str, dict[str, int]]:
    if len({r.run_id for r in results}) != len(results):
        raise ValueError("duplicate trajectory result")
    counts = Counter(r.outcome for r in results)
    live = Counter(r.outcome for r in results if r.execution_kind == ExecutionKind.LIVE)
    return {
        "counts": {name: counts[name] for name in ("pass", "fail", "unknown", "not_applicable")},
        "live_counts": {name: live[name] for name in ("pass", "fail", "unknown", "not_applicable")},
    }
