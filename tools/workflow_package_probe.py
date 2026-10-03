"""Exercise the installed optional checkpoint CLI from outside the checkout."""

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workflow-probe-") as directory:
        database = Path(directory) / "runs.db"

        def invoke(operation: str, *args: str) -> dict[str, object]:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "procurement_intelligence_lab.interfaces.workflow",
                    "--database",
                    str(database),
                    operation,
                    "--project",
                    "atlas",
                    *args,
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(process.stdout)

        view = invoke("start", "--item", "GPU-A", "--as-of", "2026-10-01T00:00:00Z")
        assert view["status"] == "awaiting_review" and view["execution_kind"] == "fixture"
        assert invoke("status", "--run-id", str(view["run_id"])) == view
        brief = view["brief"]
        assert isinstance(brief, dict)
        facts = json.loads(brief["content_json"])
        assert facts["required_quantity"] == "8" and facts["ordered_quantity"] == "6"
        args = (
            "--run-id",
            str(view["run_id"]),
            "--brief-id",
            brief["brief_id"],
            "--digest",
            brief["digest"],
            "--decision",
            "approve",
        )
        first = invoke("review", *args)
        assert first["status"] == "completed" and first["saved"]
        assert invoke("review", *args) == first
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT COUNT(*) FROM saved_briefs").fetchone()[0] == 1
    print("installed fixture workflow restart/review/save passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
