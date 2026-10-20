import json
from dataclasses import asdict
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces import document_review as cli
from tests.contract.test_document_review_journal import setup

pytestmark = pytest.mark.contract


def test_real_parser_paths_and_typed_failures(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    _, archive, p, _ = setup(archive_dsn, tmp_path)
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setenv("PIL_DOCUMENT_REVIEWER_ID", "human-parser")
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(asdict(p.scope)))
    request = tmp_path / "request.json"

    def run(*args: str, expected: int = 0):
        monkeypatch.setattr("sys.argv", ["document_review", *args])
        assert cli.main() == expected
        captured = capsys.readouterr()
        assert not (captured.err if expected == 0 else captured.out)
        return json.loads(captured.out if expected == 0 else captured.err)

    run("init")
    base = {
        "request_id": "parser-1",
        "snapshot_id": p.snapshot_id,
        "assertion_id": p.previous.assertion_id,
        "workflow": "document_value",
        "proposed_value": {"type": "decimal", "value": "8.00"},
        "reason": "correct",
    }
    request.write_text(json.dumps(base))
    task = run("propose", "--scope", str(scope), "--input", str(request))["task"]
    assert task["previous_value"]["value"] == "0.5"
    request.write_text(
        json.dumps(
            {
                "request_id": "parser-d",
                "task_id": task["task_id"],
                "task_digest": task["digest"],
                "outcome": "reject",
                "reason": "source is correct",
            }
        )
    )
    rejected = run("decide", "--scope", str(scope), "--input", str(request))
    assert rejected["decision"]["outcome"] == "reject" and rejected["correction"] is None
    assert run("show", "--scope", str(scope), "--task-id", task["task_id"]) == rejected
    assert len(run("history", "--scope", str(scope))["reviews"]) == 1
    assert (
        run(
            "show",
            "--scope",
            str(scope),
            "--task-id",
            task["task_id"],
            "--as-of",
            task["recorded_at"],
        )["decision"]
        is None
    )
    for at in ("invalid", "2026-01-01T00:00:00"):
        run("history", "--scope", str(scope), "--as-of", at, expected=2)
    for content in ("[]", "{}", '{"request_id":"one","request_id":"two"}'):
        request.write_text(content)
        run("propose", "--scope", str(scope), "--input", str(request), expected=2)
    for value in (
        None,
        {},
        {"type": "decimal", "value": "NaN"},
        {"type": "decimal", "value": "bad"},
        {"type": "decimal", "value": 1},
    ):
        request.write_text(json.dumps({**base, "proposed_value": value}))
        run("propose", "--scope", str(scope), "--input", str(request), expected=2)
    request.write_text(json.dumps({**base, "workflow": "unknown"}))
    run("propose", "--scope", str(scope), "--input", str(request), expected=2)
    request.write_text(
        json.dumps(
            {
                "request_id": "x",
                "task_id": task["task_id"],
                "task_digest": task["digest"],
                "outcome": "unknown",
                "reason": "bad",
            }
        )
    )
    run("decide", "--scope", str(scope), "--input", str(request), expected=2)
    _, snapshot = archive.load(p.scope, p.snapshot_id)
    sku = next(a for a in snapshot.assertions if a.predicate.value == "has_sku")
    for value in ({"type": "str", "value": "NEW-SKU"}, {"type": "null", "value": None}):
        request.write_text(
            json.dumps(
                {
                    **base,
                    "request_id": "text-" + str(value["type"]),
                    "assertion_id": sku.assertion_id,
                    "proposed_value": value,
                }
            )
        )
        assert (
            run("propose", "--scope", str(scope), "--input", str(request))["task"]["proposed_value"]
            == value
        )
    monkeypatch.delenv("PIL_DOCUMENT_REVIEWER_ID")
    run("history", "--scope", str(scope), expected=2)
    monkeypatch.setenv("PIL_DOCUMENT_REVIEWER_ID", "human")
    request.unlink()
    run("propose", "--scope", str(scope), "--input", str(request), expected=2)
    monkeypatch.setenv(
        "PIL_ASSERTION_ARCHIVE_DSN", "postgresql://canary:private@127.0.0.1:1/absent"
    )
    error = run("history", "--scope", str(scope), expected=2)
    assert "canary" not in json.dumps(error) and "private" not in json.dumps(error)
