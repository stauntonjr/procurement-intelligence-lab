"""Actual installed original-source CLI and policy identity, without model calls."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_order_comparison,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


def main() -> int:
    context = RequestContext(
        "local-demo",
        "synthetic-tenant",
        "synthetic-project",
        "synthetic-site",
        frozenset(Permission),
        "installed-oracle",
    )
    with tempfile.TemporaryDirectory(prefix="original-showcase-probe-") as directory:
        for sources, scenario in (
            ("showcase-a-order", ShowcaseScenario.ORDER_MISMATCH),
            ("showcase-a-b-order", ShowcaseScenario.ORDER_UNRESOLVED),
            ("showcase-a-only", ShowcaseScenario.ORDER_MISSING),
        ):
            database = Path(directory) / (sources + ".db")

            def invoke(
                operation: str,
                *args: str,
                source_choice: str = sources,
                database_path: Path = database,
            ) -> dict[str, Any]:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "procurement_intelligence_lab.interfaces.workflow",
                        "--database",
                        str(database_path),
                        "--project",
                        "synthetic-project",
                        "--sources",
                        source_choice,
                        operation,
                        *args,
                    ],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return json.loads(result.stdout)

            view = invoke("start", "--item", "GPU-A", "--as-of", "2026-01-15T00:00:00Z")
            baseline = showcase_order_comparison(scenario, request_context=context)
            facts = json.loads(view["brief"]["content_json"])
            assessment = next(
                a for a in baseline.assessments if a.kind.value == "quantity_mismatch"
            )
            assert facts["assessment_id"] == assessment.assessment_id
            assert facts["governance_decision_id"] == baseline.requirement.decision.decision_id
            assert facts["policy_id"] == assessment.policy_id
            assert facts["ordered_quantity"] == (
                str(baseline.ordered_quantity) if baseline.ordered_quantity is not None else None
            )
            assert invoke("recover", "--run-id", view["run_id"]) == view
            review_args = (
                "--run-id",
                view["run_id"],
                "--brief-id",
                view["brief"]["brief_id"],
                "--digest",
                view["brief"]["digest"],
                "--decision",
                "approve",
            )
            saved = invoke("review", *review_args)
            assert saved["status"] == "completed" and saved["saved"] is not None
            assert invoke("review", *review_args) == saved
    print(
        "installed original source CLI/policy/restart/idempotent-save probe passed; zero model calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
