"""Exercise installed archive commands outside the source checkout on a disposable database."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def main() -> int:
    base = os.environ.get("PIL_TEST_POSTGRES_DSN")
    if not base:
        print("storage package qualification not requested: set PIL_TEST_POSTGRES_DSN")
        return 0
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    schema = "pil_package_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    env = {
        **os.environ,
        "PIL_ASSERTION_ARCHIVE_DSN": make_conninfo(base, options=f"-c search_path={schema}"),
        "PIL_DOCUMENT_REVIEWER_ID": "installed-human-reviewer",
    }
    source = Path("archive-source.xlsx").absolute()
    content = Path(sys.argv[1]).read_bytes()
    source.write_bytes(content)

    def run(module: str, *args: str, success: bool = True):
        result = subprocess.run(
            [sys.executable, "-m", f"procurement_intelligence_lab.interfaces.{module}", *args],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if success:
            if result.returncode != 0:
                raise RuntimeError("installed archive command failed: " + result.stderr)
        elif result.returncode != 2 or result.stdout:
            raise RuntimeError("installed archive command failed to reject invalid export")
        return result

    try:
        run("assertion_archive", "init")
        args = (
            str(source),
            "--context",
            sys.argv[2],
            "--normalization-policy",
            sys.argv[3],
            "--assertions",
            "--archive",
        )
        first = run("bom_stages", *args)
        if first.stdout != run("bom_stages", *args).stdout:
            raise RuntimeError("archive retry changed receipt")
        payload = json.loads(first.stdout)
        receipt = payload["archive_receipt"]
        quantity = next(
            x
            for x in payload["assertion_batch"]["claims"]
            if x["trace"]["mapped_field_key"] == "BOM!C2"
        )
        if quantity["value"] != "4" or quantity["evidence"]["cells"] != ["C"]:
            raise RuntimeError("installed archive lost quantity/evidence")
        scope = Path("archive-scope.json").absolute()
        scope.write_text(json.dumps(receipt["scope"]))
        source.unlink()
        shown = run(
            "assertion_archive",
            "show",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
        )
        if json.loads(shown.stdout) != payload:
            raise RuntimeError("archive reconstruction changed retained source result")
        output = Path("archive-retained.xlsx").absolute()
        export_args = (
            "content",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
            "--output",
            str(output),
        )
        run("assertion_archive", *export_args)
        if output.read_bytes() != content:
            raise RuntimeError("archive export changed captured bytes")
        run("assertion_archive", *export_args, success=False)
        run("document_review", "init")
        proposal = Path("document-review-proposal.json").absolute()
        proposal.write_text(
            json.dumps(
                {
                    "request_id": "installed-task",
                    "snapshot_id": receipt["snapshot_id"],
                    "assertion_id": quantity["assertion_id"],
                    "workflow": "document_value",
                    "proposed_value": {"type": "decimal", "value": "8.00"},
                    "reason": "Check source interpretation",
                }
            )
        )
        task_args = ("propose", "--scope", str(scope), "--input", str(proposal))
        proposed = run("document_review", *task_args)
        if proposed.stdout != run("document_review", *task_args).stdout:
            raise RuntimeError("installed review retry changed task/time")
        task = json.loads(proposed.stdout)["task"]
        if task["previous_value"] != {"type": "decimal", "value": "4"} or task["evidence"][
            "cells"
        ] != ["C"]:
            raise RuntimeError("installed task lost previous value/source evidence")
        decision = Path("document-review-decision.json").absolute()
        command = {
            "request_id": "installed-decision",
            "task_id": task["task_id"],
            "task_digest": task["digest"],
            "outcome": "approve",
            "reason": "Checked captured evidence",
        }
        decision.write_text(json.dumps({**command, "task_digest": "0" * 64}))
        run(
            "document_review",
            "decide",
            "--scope",
            str(scope),
            "--input",
            str(decision),
            success=False,
        )
        decision.write_text(json.dumps(command))
        decision_args = ("decide", "--scope", str(scope), "--input", str(decision))
        accepted = run("document_review", *decision_args)
        if accepted.stdout != run("document_review", *decision_args).stdout:
            raise RuntimeError("installed review retry changed decision/time")
        correction = json.loads(accepted.stdout)["correction"]
        if (
            correction["value"] != {"type": "decimal", "value": "8.00"}
            or not correction["recomputation_required"]
            or correction["downstream_status"] != "not_evaluated"
            or correction["governing_state_updated"]
        ):
            raise RuntimeError("installed correction changed scope or authority semantics")
        shown_review = run(
            "document_review", "show", "--scope", str(scope), "--task-id", task["task_id"]
        )
        if shown_review.stdout != accepted.stdout:
            raise RuntimeError("installed review reconstruction changed lineage")
        historical = run(
            "document_review",
            "show",
            "--scope",
            str(scope),
            "--task-id",
            task["task_id"],
            "--as-of",
            task["recorded_at"],
        )
        if json.loads(historical.stdout)["correction"] is not None:
            raise RuntimeError("future correction leaked into earlier view")
        original_again = run(
            "assertion_archive",
            "show",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
        )
        if json.loads(original_again.stdout) != payload:
            raise RuntimeError("human review rewrote original source claims")
        scope.write_text(json.dumps({**receipt["scope"], "tenant_id": "foreign"}))
        denied = run(
            "assertion_archive",
            "show",
            "--scope",
            str(scope),
            "--snapshot-id",
            receipt["snapshot_id"],
            success=False,
        )
        if json.loads(denied.stderr)["code"] != "pil.input.archive_not_found":
            raise RuntimeError("foreign archive scope was not isolated")
        print(
            json.dumps(
                {
                    "storage_package_smoke": "passed",
                    "document_review_smoke": "passed",
                    "assertions": len(payload["assertion_batch"]["claims"]),
                    "source_deleted": True,
                    "retry_equal": True,
                    "export_equal": True,
                }
            )
        )
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
