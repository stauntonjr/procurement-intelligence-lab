"""Failure probes cannot masquerade as completed or real-model acceptance."""

from typing import Any

import pytest

from tools.run_g2_adversarial import CASES, summarize


def observations() -> list[dict[str, Any]]:
    return [
        {
            "id": name,
            "outcome": "pass",
            "kind": kind,
            "attempt_complete": True,
            "terminal_calls": 0 if name == "request_guards" else 1,
            "real_qwen_calls": int(kind == "real_qwen"),
            "controlled_protocol_calls": int(
                kind == "controlled_protocol" and name != "request_guards"
            ),
            "tool_starts": 0,
            "saved_count": int(name == "review_crash_scope"),
        }
        for name, kind in CASES.items()
    ]


def test_closed_denominator_keeps_omitted_case_unknown() -> None:
    rows = observations()[:-1]
    report = summarize(rows)
    assert report["counts"]["unknown"] == 1
    assert not report["ready"]


@pytest.mark.parametrize("change", ["duplicate", "foreign", "unfinished", "fake_real"])
def test_fabricated_or_incomplete_completion_cannot_pass(change: str) -> None:
    rows = observations()
    if change == "duplicate":
        rows.append(rows[0])
    elif change == "foreign":
        rows[0] = rows[0] | {"id": "foreign"}
    elif change == "unfinished":
        rows[0]["attempt_complete"] = False
    else:
        rows[1]["real_qwen_calls"] = 1
    report = summarize(rows)
    assert not report["ready"]


def test_protocol_only_is_not_live_acceptance_and_counts_are_separate() -> None:
    rows = [row for row in observations() if row["kind"] == "controlled_protocol"]
    report = summarize(rows, protocol_only=True)
    assert report["counts"] == {"pass": 4, "fail": 0, "unknown": 0, "not_applicable": 5}
    assert not report["ready"]
    assert report["real_qwen_calls"] == 0
    assert report["controlled_protocol_calls"] == 3


def test_failed_guard_keeps_actual_terminal_call_in_denominator() -> None:
    rows = observations()
    rows[4]["outcome"] = "fail"
    report = summarize(rows)
    assert report["counts"]["fail"] == 1
    assert report["real_qwen_calls"] == 5
    assert not report["ready"]


def test_missing_attempt_count_is_unknown_instead_of_zero():
    report = summarize(observations()[:-1])
    assert report["real_qwen_calls"] is None
