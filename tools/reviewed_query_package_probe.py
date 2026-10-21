"""Exercise the installed reviewed query against the caller's isolated archive/review schema."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    scope, snapshot_id, task_id, original_context, revision = sys.argv[1:]

    def run(module: str, *args: str, success: bool = True):
        result = subprocess.run(
            [sys.executable, "-m", f"procurement_intelligence_lab.interfaces.{module}", *args],
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        if success and result.returncode != 0:
            raise RuntimeError("installed reviewed probe command failed: " + result.stderr)
        if not success and (result.returncode != 2 or result.stdout):
            raise RuntimeError("installed reviewed probe failed to reject unavailable capability")
        return result

    original_args = (
        "--scope",
        scope,
        "--snapshot-id",
        snapshot_id,
        "--request-id",
        "installed-source-skus",
        "--context",
        original_context,
    )
    original = run("archived_bom_query", *original_args)
    selection = Path("installed-selected-reviews.json").absolute()
    selection.write_text(json.dumps({"task_ids": [task_id]}))
    as_of = datetime.now(UTC).isoformat()
    context = Path("installed-reviewed-context.json").absolute()
    context.write_text(
        json.dumps(
            {
                "run_id": "installed-reviewed-replay",
                "code_revision": revision,
                "started_at": datetime.now(UTC).isoformat(),
            }
        )
    )
    args = (
        "--scope",
        scope,
        "--snapshot-id",
        snapshot_id,
        "--request-id",
        "installed-reviewed-skus",
        "--reviews",
        str(selection),
        "--as-of",
        as_of,
        "--context",
        str(context),
    )
    missing = run("reviewed_bom_query", *args, success=False)
    if json.loads(missing.stderr)["code"] != "pil.infrastructure.dependency_unavailable":
        raise RuntimeError("reviewed replay did not require explicit correction-root capability")
    initialized = run("correction_impact", "init-reviewed")
    if json.loads(initialized.stdout) != {
        "capability": "approved_correction_roots/v1",
        "initialized": True,
    }:
        raise RuntimeError("reviewed capability initialization contract differs")
    if run("correction_impact", "init-reviewed").stdout != initialized.stdout:
        raise RuntimeError("reviewed capability initialization is not idempotent")
    result = run("reviewed_bom_query", *args)
    body = json.loads(result.stdout)
    query = body["reviewed_query"]
    source = json.loads(original.stdout)["query"]
    if (
        query["value"] != ["CPU-A", "GPU-CHANGED"]
        or query["status"] != "inferred"
        or query["reference_id"] == source["reference_id"]
        or not body["recomputation_executed"]
        or body["original_source_updated"]
        or body["governing_state_updated"]
        or body["query_result_materialized"]
        or body["correction_selection"] != "explicit_selected_set"
        or body["unselected_reviews"] != "not_evaluated"
        or query["producer_event"]["provenance"]["context"]["code_revision"] != revision
    ):
        raise RuntimeError("installed reviewed query value/provenance/boundary differs")
    row = query["reviewed_rows"][0]
    correction = body["selected_reviews"][0]["correction"]
    if (
        {e["target_id"] for e in row["producer_event"]["input_edges"]}
        != {row["source_assertion_id"], correction["correction_id"]}
        or {e["relation"] for e in row["producer_event"]["input_edges"]} != {"used_input"}
        or row["reference_id"]
        not in {e["target_id"] for e in query["producer_event"]["input_edges"]}
    ):
        raise RuntimeError("reviewed replay omitted correction value data dependency")
    if run("reviewed_bom_query", *args).stdout != result.stdout:
        raise RuntimeError("installed reviewed replay retry changed result/first receipt")
    if run("archived_bom_query", *original_args).stdout != original.stdout:
        raise RuntimeError("reviewed replay changed the original immutable source query")
    retained = Path("reviewed-retained.xlsx").absolute()
    run(
        "assertion_archive",
        "content",
        "--scope",
        scope,
        "--snapshot-id",
        snapshot_id,
        "--output",
        str(retained),
    )
    if (
        retained.read_bytes() != Path("archive-retained.xlsx").read_bytes()
        or Path("archive-source.xlsx").exists()
    ):
        raise RuntimeError("reviewed replay changed archived source bytes/deletion boundary")
    print(
        json.dumps(
            {
                "reviewed_source_query_smoke": "passed",
                "explicit_capability": True,
                "original_query_unchanged": True,
                "source_deleted": True,
                "retry_equal": True,
                "export_equal": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
