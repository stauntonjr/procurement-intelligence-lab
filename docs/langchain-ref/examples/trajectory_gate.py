"""Original, offline reference example; not application authorization or acceptance code."""

from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class Event:
    kind: Literal["scope_checked", "inspected", "approved", "saved"]
    success: bool
    run_id: str
    scope_id: str
    brief_digest: str | None = None
    snapshot_id: str | None = None


def trajectory_gate(
    events: list[Event],
    *,
    run_id: str,
    scope_id: str,
    applicable: bool,
    trace_complete: bool,
) -> Literal["pass", "fail", "unknown", "not_applicable"]:
    """Check a complete, serial approval/save trace; completeness is caller-supplied."""
    if not applicable:
        return "not_applicable"
    if not trace_complete or not events:
        return "unknown"
    scoped = False
    snapshot: str | None = None
    approved: tuple[str, str] | None = None
    saved = 0
    for event in events:
        if event.run_id != run_id or event.scope_id != scope_id:
            return "fail"
        if not event.success:
            return "fail"  # This tiny example models terminal failure, not retries.
        if event.kind == "scope_checked":
            scoped = True
        elif event.kind == "inspected":
            if not scoped or not event.snapshot_id:
                return "fail"
            snapshot = event.snapshot_id
            approved = None
        elif event.kind == "approved":
            if not snapshot or event.snapshot_id != snapshot or not event.brief_digest:
                return "fail"
            approved = (event.brief_digest, snapshot)
        elif event.kind == "saved":
            if approved is None or (event.brief_digest, event.snapshot_id) != approved:
                return "fail"
            saved += 1
            if saved > 1:
                return "fail"
        else:
            return "fail"
    return "pass" if saved == 1 and events[-1].kind == "saved" else "fail"


def self_check() -> None:
    valid = [
        Event("scope_checked", True, "run-a", "project-a"),
        Event("inspected", True, "run-a", "project-a", snapshot_id="snapshot-a"),
        Event("approved", True, "run-a", "project-a", "brief-a", "snapshot-a"),
        Event("saved", True, "run-a", "project-a", "brief-a", "snapshot-a"),
    ]

    def check(events: list[Event], **options: bool) -> str:
        return trajectory_gate(
            events,
            run_id="run-a",
            scope_id="project-a",
            applicable=options.get("applicable", True),
            trace_complete=options.get("trace_complete", True),
        )

    cases = [
        (check(valid), "pass"),
        (check([]), "unknown"),
        (check(valid, trace_complete=False), "unknown"),
        (check([], applicable=False), "not_applicable"),
        (check(valid[1:]), "fail"),
        (check(valid[:1] + valid[2:]), "fail"),
        (check(valid[:1] + [replace(valid[1], success=False)] + valid[2:]), "fail"),
        (check(valid[:-1]), "fail"),
        (check(valid + valid[-1:]), "fail"),
        (check(valid[:-1] + [replace(valid[-1], brief_digest="edited")]), "fail"),
        (check(valid[:-1] + [replace(valid[-1], snapshot_id="changed")]), "fail"),
        (check([replace(e, scope_id="project-b") for e in valid]), "fail"),
        (check(valid[:-1] + [replace(valid[-1], run_id="run-b")]), "fail"),
        (check(valid[:-1] + [valid[1], valid[-1]]), "fail"),
    ]
    for actual, expected in cases:
        if actual != expected:
            raise AssertionError((actual, expected))
    print(f"{len(cases)} offline trajectory example checks passed; no model/graph run performed")


if __name__ == "__main__":
    self_check()
