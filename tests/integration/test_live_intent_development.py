"""Opt-in actual installed CLI evaluation; CI never calls a model.

Run with PIL_INTENT_PYTHON, PIL_INTENT_DATABASE and PIL_INTENT_OUTPUT pointing to a
clean installed wheel and fresh evidence paths. Every case runs once; failures are
retained before assertion. The controls are development data, not held-out quality.
"""

import json
import os
import sqlite3
import subprocess
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab.interfaces.live_review import compose_live
from tools.g2_pilot_scoring import score_intent
from tools.run_g2_pilot import audit_attempts, reconcile_attempts

MANIFEST = (
    Path(__file__).resolve().parents[2] / "evals/operational_agents/intent-development-v1.json"
)


@pytest.mark.skipif(
    not os.environ.get("PIL_INTENT_PYTHON"), reason="explicit local live opt-in required"
)
def test_installed_live_intent_development() -> None:
    python = Path(os.environ["PIL_INTENT_PYTHON"]).absolute()
    database = Path(os.environ["PIL_INTENT_DATABASE"]).absolute()
    output = Path(os.environ["PIL_INTENT_OUTPUT"]).absolute()
    assert not database.exists() and not output.exists(), "never overwrite prior evidence"
    cases = json.loads(MANIFEST.read_text())["cases"]
    versions = asdict(compose_live(database).runs.versions)
    probe = (
        "import json,tempfile; from pathlib import Path; from dataclasses import asdict; "
        "from procurement_intelligence_lab.interfaces.live_review import compose_live; "
        'print(json.dumps(asdict(compose_live(Path(tempfile.mkdtemp())/"probe.db").runs.versions)))'
    )
    installed = json.loads(
        subprocess.check_output([str(python), "-c", probe], cwd="/tmp", text=True)
    )
    assert installed == versions, "installed bytes must match frozen checkout"
    report: dict[str, Any] = {
        "evaluation_use": "development",
        "manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
        "versions": versions,
        "application_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "runs": [],
    }

    def retain() -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, default=str) + "\n")

    retain()
    for case in cases:
        record: dict[str, Any] = {"id": case["id"], "outcome": "unknown"}
        report["runs"].append(record)
        retain()
        try:
            result = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.live_review",
                    "--database",
                    str(database),
                    "--project",
                    case["project"],
                    "ask",
                    "--question",
                    case["question"],
                    "--as-of",
                    case["as_of"],
                ],
                cwd="/tmp",
                check=False,
                text=True,
                capture_output=True,
                timeout=60,
            )
            raw_outcome = json.loads(result.stdout)
            if not isinstance(raw_outcome, dict):
                raise TypeError("malformed public outcome")
            outcome = cast(dict[str, Any], raw_outcome)
            errors = score_intent(case, outcome)
            if result.returncode:
                errors.append("public_exit")
            view = outcome.get("workflow")
            if view is not None and (
                view.get("saved") is not None or view.get("status") != "awaiting_review"
            ):
                errors.append("model_save_authority")
            record.update(
                interpretation=outcome.get("interpretation"),
                errors=errors,
                outcome="fail" if errors else "pass",
            )
        except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as error:
            record["error"] = type(error).__name__
        retain()
    report["attempt_audit"] = audit_attempts(database, cases)
    report["runs"], report["attempt_audit_complete"] = reconcile_attempts(
        cases, report["runs"], report["attempt_audit"]
    )
    with sqlite3.connect(database) as connection:
        report["saved_results"] = connection.execute(
            "SELECT COUNT(*) FROM saved_briefs"
        ).fetchone()[0]
    retain()
    assert report["attempt_audit_complete"]
    assert report["saved_results"] == 0
    assert len(report["runs"]) == len(cases) == 20
    assert all(row["model_calls"] == 1 for row in report["attempt_audit"])
    failures = [row for row in report["runs"] if row["outcome"] != "pass"]
    assert not failures, json.dumps(failures)
