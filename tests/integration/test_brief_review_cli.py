"""Public human CLI process exit/restart and exact-request failure evidence."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def invoke(
    path: Path, operation: str, *args: str, project: str = "atlas"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.briefs",
            "--database",
            str(path),
            operation,
            "--project",
            project,
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def create(path: Path) -> str:
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.agent_runs",
            "--database",
            str(path),
            "create",
            "--project",
            "atlas",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return str(json.loads(p.stdout)["run_id"])


def draft(path: Path, run_id: str, item: str = "GPU-A") -> dict[str, Any]:
    p = invoke(path, "draft", "--run-id", run_id, "--item", item, "--as-of", "2026-10-01T00:00:00Z")
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(p.stdout)


def test_public_draft_review_save_restart_exactly_once(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    run_id = create(path)
    brief = draft(path, run_id)
    facts = json.loads(brief["content_json"])
    assert facts["required_quantity"] == "8" and facts["ordered_quantity"] == "6"
    assert facts["evidence"] and facts["policy_id"]
    args = ["--run-id", run_id, "--brief-id", brief["brief_id"], "--digest", brief["digest"]]
    denied = invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"])
    assert denied.returncode == 1 and json.loads(denied.stdout)["category"] == "policy"
    review = invoke(path, "review", *args, "--decision", "approve")
    assert review.returncode == 0, review.stdout + review.stderr
    assert json.loads(review.stdout)["reviewer_id"] == "local-demo"
    first = invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"])
    second = invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"])
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)
    foreign = invoke(
        path, "show", "--run-id", run_id, "--brief-id", brief["brief_id"], project="delta"
    )
    assert (
        foreign.returncode == 1
        and json.loads(foreign.stdout)["code"] == "pil.input.agent_run_not_found"
    )
    altered = invoke(
        path,
        "save",
        "--run-id",
        run_id,
        "--brief-id",
        brief["brief_id"],
        "--digest",
        "0" * 64,
        "--idempotency-key",
        brief["idempotency_key"],
    )
    assert altered.returncode == 1 and json.loads(altered.stdout)["category"] == "policy"
    malformed = invoke(path, "review", *args, "--decision", "approve", "--permissions", "act")
    assert malformed.returncode != 0


def test_rejection_and_replacement_at_public_boundary(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    run_id = create(path)
    brief = draft(path, run_id, "GPU-C")
    assert json.loads(brief["content_json"])["required_quantity"] is None
    args = ["--run-id", run_id, "--brief-id", brief["brief_id"], "--digest", brief["digest"]]
    assert invoke(path, "review", *args, "--decision", "reject").returncode == 0
    assert (
        invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"]).returncode == 1
    )
    new = draft(path, run_id, "GPU-D")
    assert new["version"] == 2 and json.loads(new["content_json"])["ordered_quantity"] is None
    assert invoke(path, "review", *args, "--decision", "approve").returncode == 1


def test_public_parser_preserves_failure_envelopes_in_host_process(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    # Same entry point as the subprocess cases; exercise early failures without
    # replacing its context, service or adapter. Host coverage can observe this path.
    from procurement_intelligence_lab.interfaces.briefs import main

    for project, extra, code in [
        ("unknown-project", [], "pil.authorization.request_scope_denied"),
        ("atlas", ["--run-id", "missing"], "pil.input.semantic_contract_violation"),
    ]:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "briefs",
                "--database",
                str(tmp_path / "runs.db"),
                "review",
                "--project",
                project,
                *extra,
            ],
        )
        assert main() == 1
        assert json.loads(capsys.readouterr().out)["code"] == code


def test_public_save_acknowledges_replaced_saved_brief(tmp_path: Path) -> None:
    path = tmp_path / "r.db"
    run_id = create(path)
    brief = draft(path, run_id, "GPU-A")
    args = ["--run-id", run_id, "--brief-id", brief["brief_id"], "--digest", brief["digest"]]
    assert invoke(path, "review", *args, "--decision", "approve").returncode == 0
    first = invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"])
    assert first.returncode == 0, first.stderr
    draft(path, run_id, "GPU-A")
    replay = invoke(path, "save", *args, "--idempotency-key", brief["idempotency_key"])
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout) == json.loads(first.stdout)


def test_public_save_translates_vanished_item(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    from procurement_intelligence_lab.application.corpus_investigation import (
        CorpusInvestigationService,
    )
    from procurement_intelligence_lab.interfaces.briefs import main
    from procurement_intelligence_lab.ports.corpus import CorpusNotFoundError

    path = tmp_path / "r.db"
    run_id = create(path)
    brief = draft(path, run_id, "GPU-A")
    args = ["--run-id", run_id, "--brief-id", brief["brief_id"], "--digest", brief["digest"]]
    assert invoke(path, "review", *args, "--decision", "approve").returncode == 0

    def vanished(*args: Any, **kwargs: Any) -> Any:
        raise CorpusNotFoundError("private vanished item")

    monkeypatch.setattr(CorpusInvestigationService, "investigate", vanished)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "briefs",
            "--database",
            str(path),
            "save",
            "--project",
            "atlas",
            *args,
            "--idempotency-key",
            brief["idempotency_key"],
        ],
    )
    assert main() == 1
    output = capsys.readouterr().out
    assert json.loads(output)["code"] == "pil.policy.brief_review_conflict"
    assert "private" not in output
