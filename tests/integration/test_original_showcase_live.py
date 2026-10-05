"""Opt-in installed browser compatibility with original fixtures and actual local Qwen."""

import json
import os
import subprocess
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_order_comparison,
)
from procurement_intelligence_lab.interfaces.live_review import compose_live
from tests.contract.test_original_showcase_sources import CONTEXT
from tests.integration.test_browser_review import (
    chromium_page,
    installed_reviewer,
    ledger,
    review,
    sign_in,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PIL_ORIGINAL_LIVE") != "1" or not os.environ.get("PIL_BROWSER_PYTHON"),
    reason="explicit original installed live-browser opt-in required",
)


def test_original_showcase_installed_live_browser() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / "evals/operational_agents/original-showcase-browser-v1.json"
    manifest = json.loads(manifest_path.read_text())
    output = Path(os.environ["PIL_ORIGINAL_OUTPUT"]).absolute()
    assert not output.exists(), "fresh output required; never overwrite evidence"
    output.mkdir(parents=True)
    scenarios = {
        "showcase-a-order": ShowcaseScenario.ORDER_MISMATCH,
        "showcase-a-b-order": ShowcaseScenario.ORDER_UNRESOLVED,
        "showcase-a-only": ShowcaseScenario.ORDER_MISSING,
    }
    records = [
        {"sources": case["sources"], "repetition": n, "outcome": "unknown"}
        for case in manifest["cases"]
        for n in range(1, manifest["repetitions"] + 1)
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "wheel_sha256": sha256(Path(os.environ["PIL_ORIGINAL_WHEEL"]).read_bytes()).hexdigest(),
        "execution_kind": "live",
        "application_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "limits": manifest["limits"],
        "runs": records,
        "versions": {},
        "acceptance": "not_ready",
    }

    def retain() -> None:
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    retain()
    try:
        with chromium_page() as page:
            report["browser"] = page.context.browser.version if page.context.browser else "unknown"
            for case in manifest["cases"]:
                selection = case["sources"]
                directory = output / selection
                directory.mkdir()
                versions = asdict(
                    compose_live(directory / "review.db", sources=selection).runs.versions
                )
                probe = (
                    "import json,tempfile; from pathlib import Path; from dataclasses import asdict; "
                    "from procurement_intelligence_lab.interfaces.live_review import compose_live; "
                    f'print(json.dumps(asdict(compose_live(Path(tempfile.mkdtemp())/"probe.db",sources={selection!r}).runs.versions)))'
                )
                installed = json.loads(
                    subprocess.check_output(
                        [os.environ["PIL_BROWSER_PYTHON"], "-c", probe], cwd="/tmp", text=True
                    )
                )
                assert installed == versions
                report["versions"][selection] = versions
                direct = showcase_order_comparison(scenarios[selection], request_context=CONTEXT)
                assessment = next(
                    a for a in direct.assessments if a.kind.value == "quantity_mismatch"
                )
                with ExitStack() as servers:
                    server = servers.enter_context(
                        installed_reviewer(
                            directory, live=True, sources=selection, project=manifest["project"]
                        )
                    )
                    sign_in(page, server)
                    assert (
                        page.get_by_label("As of (ISO 8601 with timezone)").input_value()
                        == manifest["as_of"]
                    )
                    for record in [r for r in records if r["sources"] == selection]:
                        page.get_by_label("Question", exact=True).fill(manifest["question"])
                        with page.expect_response("**/api/ask") as response:
                            page.get_by_label("Question", exact=True).press("Enter")
                        result = response.value.json()
                        record["http_status"] = response.value.status
                        if "interpretation" in result:
                            record["interpretation"] = result["interpretation"]
                            retain()
                        assert (
                            response.value.status == 200
                            and result["interpretation"]["status"] == "investigate"
                        )
                        view = result["workflow"]
                        record["run_id"] = view["run_id"]
                        facts = json.loads(view["brief"]["content_json"])
                        assert {
                            k: facts[k]
                            for k in ("required_quantity", "ordered_quantity", "status", "reason")
                        } == {
                            k: case[k]
                            for k in ("required_quantity", "ordered_quantity", "status", "reason")
                        }
                        assert (
                            facts["governance_decision_id"]
                            == direct.requirement.decision.decision_id
                        )
                        assert (
                            facts["governance_policy_id"] == direct.requirement.decision.policy_id
                        )
                        assert facts["assessment_id"] == assessment.assessment_id
                        assert (
                            facts["policy_id"] == assessment.policy_id
                            and facts["policy_digest"] == assessment.policy_digest
                        )
                        assert facts["input_dispositions"] == dict(assessment.input_dispositions)
                        assert facts["governance_dispositions"] == dict(
                            direct.requirement.decision.dispositions
                        )
                        assert {ref["evidence_id"] for ref in facts["evidence"]} == set(
                            case["evidence_ids"]
                        )
                        expect(page.locator("#review-title")).to_be_focused()
                        expect(page.locator("#outcome")).to_contain_text(
                            "Order observation: " + (case["ordered_quantity"] or "not established")
                        )
                        expect(page.locator("#outcome")).to_contain_text(case["status"])
                        expect(
                            page.get_by_role("button", name="Investigate and draft")
                        ).to_be_enabled()
                        expect(page.locator("#evidence button").first).to_have_attribute(
                            "aria-pressed", "true"
                        )
                        for i, ref in enumerate(facts["evidence"]):
                            with page.expect_response("**/api/source?*") as source_response:
                                button = page.locator("#evidence button").nth(i)
                                button.focus()
                                button.press("Enter")
                            source = source_response.value.json()
                            assert source_response.value.status == 200 and source["evidence"] == ref
                            expect(button).to_have_attribute("aria-pressed", "true")
                            assert (
                                page.locator('#evidence button[aria-pressed="true"]').count() == 1
                            )
                            expect(page.locator("#source .source-note")).to_have_text(
                                "Highlighted cells support this finding."
                            )
                            expect(page.locator("#source td")).to_have_text(source["cells"])
                            expect(page.locator("#source td.highlight")).to_have_text(
                                [
                                    source["cells"][ord(c) - ord("A")]
                                    for c in source["highlighted_columns"]
                                ]
                            )
                            expect(
                                page.get_by_role("button", name="Investigate and draft")
                            ).to_be_enabled()
                        record["source_count"] = len(facts["evidence"])
                        if record["repetition"] == 1:
                            port = urlsplit(server.origin).port
                            assert port is not None
                            servers.close()
                            server = servers.enter_context(
                                installed_reviewer(
                                    directory,
                                    live=True,
                                    sources=selection,
                                    project=manifest["project"],
                                    port=port,
                                )
                            )
                            sign_in(page, server)
                            with page.expect_response("**/api/interpretation?*"):
                                page.locator("#runs button").first.click()
                            expect(page.locator("#identity")).to_contain_text(
                                view["brief"]["brief_id"]
                            )
                            with page.expect_response("**/api/recover") as recovered:
                                page.get_by_role("button", name="Recover selected run").click()
                            assert recovered.value.json() == result
                            record["process_restart_recovered"] = True
                        decision = (
                            "reject"
                            if selection == "showcase-a-b-order" and record["repetition"] == 1
                            else "approve"
                        )
                        reviewed = cast(dict[str, Any], review(page, decision))
                        if decision == "approve":
                            assert (
                                reviewed["status"] == "completed" and reviewed["saved"] is not None
                            )
                            assert review(page, decision) == reviewed
                            record["saved_id"] = reviewed["saved"]["saved_id"]
                        else:
                            assert reviewed["status"] == "rejected" and reviewed["saved"] is None
                        record.update(
                            outcome="pass",
                            decision=decision,
                            facts=facts,
                            digest=view["brief"]["digest"],
                        )
                        retain()
                    actual = cast(dict[str, Any], ledger(directory / "review.db", live=True))
                    report.setdefault("ledgers", {})[selection] = actual
                    calls = {c["run_id"]: c for c in actual["calls"]}
                    saves = {s["run_id"]: s for s in actual["saves"]}
                    assert len(calls) == 3 and len(actual["runs"]) == 3
                    assert len(saves) == (2 if selection == "showcase-a-b-order" else 3)
                    for record in [r for r in records if r["sources"] == selection]:
                        call = calls[record["run_id"]]
                        assert (
                            call == record["interpretation"]
                            and call["question_hash"]
                            == sha256(manifest["question"].encode()).hexdigest()
                        )
                        assert datetime.fromisoformat(call["as_of"]) == datetime.fromisoformat(
                            manifest["as_of"]
                        )
                        run = next(r for r in actual["runs"] if r["run_id"] == record["run_id"])
                        assert (
                            run["versions"] == versions
                            and run["project_id"] == manifest["project"]
                            and run["site_id"] == manifest["site"]
                        )
                        assert (
                            len(
                                [
                                    e
                                    for e in actual["events"]
                                    if e["run_id"] == record["run_id"]
                                    and e["kind"] == "tool_started"
                                ]
                            )
                            == 2
                        )
                        assert (
                            saves[record["run_id"]]["saved_id"] == record["saved_id"]
                            if record.get("saved_id")
                            else record["run_id"] not in saves
                        )
                    retain()
            report["acceptance"] = "original_browser_passed"
    finally:
        for selection in scenarios:
            directory = output / selection
            (directory / "token").unlink(missing_ok=True)
            if (directory / "review.db").exists():
                report.setdefault("ledgers", {})[selection] = ledger(
                    directory / "review.db", live=True
                )
        retain()
