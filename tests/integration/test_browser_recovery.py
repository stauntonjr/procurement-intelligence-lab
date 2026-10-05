"""Actual installed browser with labeled transport faults; never inference or tracing."""

import json
import os
import re
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Page, Route, expect
from test_browser_review import chromium_page, installed_reviewer, ledger, sign_in, submit

pytestmark = pytest.mark.skipif(
    not os.environ.get("PIL_BROWSER_PYTHON"), reason="explicit installed-browser opt-in required"
)


@pytest.fixture
def case(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    root = Path(os.environ.get("PIL_BROWSER_RECOVERY_OUTPUT", str(tmp_path)))
    directory = root / re.sub(r"[^a-zA-Z0-9_-]", "_", str(cast(Any, request).node.name))
    assert not directory.exists(), "fresh case output required"
    directory.mkdir(parents=True)
    report: dict[str, Any] = {
        "id": str(cast(Any, request).node.name),
        "outcome": "unknown",
        "model_attempts": None,
        "limits": "Installed fixture/backend and controlled browser transport faults; live page is UI-only, not model quality.",
    }
    output = directory / "report.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    before = request.session.testsfailed
    try:
        yield directory, report
    finally:
        if request.session.testsfailed > before:
            report["outcome"] = "fail"
        output.write_text(json.dumps(report, indent=2) + "\n")
        (directory / "token").unlink(missing_ok=True)


def finish(directory: Path, report: dict[str, Any], page: Page, *, live: bool = False) -> None:
    actual = cast(dict[str, Any], ledger(directory / "review.db", live=live))
    assert len(actual["calls"]) == 0
    report.update(
        outcome="pass",
        model_attempts=0,
        ledger=actual,
        browser=page.context.browser.version if page.context.browser else "unknown",
    )
    assert page.evaluate("localStorage.length + sessionStorage.length") == 0
    assert not page.context.cookies()


def capture_actions(page: Page) -> None:
    # Observe completion of the real shipped callback, without changing work or authority.
    page.evaluate("""() => { const original=action; action=work=>{
        const pending=original(work); window.lastAction=pending; return pending; }; }""")


def complete_action(page: Page) -> None:
    page.evaluate("async () => { await window.lastAction; }")


def reject_transport(route: Route) -> None:
    route.fulfill(
        status=503,
        content_type="application/json",
        body=json.dumps(
            {"error": "Injected transport unavailable", "code": "pil.transient.browser_probe"}
        ),
    )


def test_failed_replacement_keeps_exact_persisted_draft(case: tuple[Path, dict[str, Any]]) -> None:
    directory, report = case
    with installed_reviewer(directory) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        view = cast(dict[str, Any], submit(page, "GPU-A", live=False))
        identity = view["brief"]["brief_id"]
        page.route("**/api/start", reject_transport)
        capture_actions(page)
        page.get_by_label("Canonical item", exact=True).fill("GPU-C")
        page.get_by_label("Canonical item", exact=True).press("Enter")
        complete_action(page)
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#identity")).to_contain_text(identity)
        expect(page.locator("#review")).to_be_visible()
        expect(page.get_by_role("button", name="Recover selected run")).to_be_enabled()
        expect(page.get_by_role("button", name="Approve exact brief", exact=True)).to_be_enabled()
        assert page.get_by_label("Canonical item", exact=True).input_value() == "GPU-C"
        report.update(brief_id=identity, run_id=view["run_id"], injected="start503_before_backend")
        finish(directory, report, page)
        assert len(report["ledger"]["runs"]) == 1 and len(report["ledger"]["saves"]) == 0


@pytest.mark.parametrize("live", [False, True], ids=["fixture", "live_page_no_inference"])
@pytest.mark.parametrize("encoding", ["text", "json"])
def test_malformed_response_is_a_safe_visible_failure(
    case: tuple[Path, dict[str, Any]], live: bool, encoding: str
) -> None:
    directory, report = case
    with installed_reviewer(directory, live=live) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        page.route(
            "**/api/ask" if live else "**/api/start",
            lambda route: route.fulfill(
                status=503,
                content_type="text/plain" if encoding == "text" else "application/json",
                body="PRIVATE_RESPONSE_FRAGMENT"
                if encoding == "text"
                else json.dumps({"error": "PRIVATE_RESPONSE_FRAGMENT", "code": "untrusted_reply"}),
            ),
        )
        capture_actions(page)
        page.get_by_role("button", name="Investigate and draft").click()
        complete_action(page)
        expect(page.locator("#error")).to_be_visible()
        assert "PRIVATE_RESPONSE_FRAGMENT" not in page.locator("#error").inner_text()
        expect(page.get_by_role("button", name="Investigate and draft")).to_be_enabled()
        expect(page.locator("#approve")).to_be_disabled()
        report.update(
            injected="malformed_response_before_backend",
            live_page_only=live,
            response_format=encoding,
        )
        finish(directory, report, page, live=live)
        assert len(report["ledger"]["runs"]) == len(report["ledger"]["saves"]) == 0


def test_lock_during_delayed_timeline_has_no_late_follow_up(
    case: tuple[Path, dict[str, Any]],
) -> None:
    directory, report = case
    with installed_reviewer(directory) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        held: list[tuple[Route, str]] = []

        def delayed(route: Route) -> None:
            response = route.fetch()
            held.append((route, response.text()))

        page.route("**/api/events?*", delayed)
        urls: list[str] = []
        page.on("request", lambda request: urls.append(request.url))
        capture_actions(page)
        with page.expect_response("**/api/start"):
            page.get_by_role("button", name="Investigate and draft").click()
        expect(page.locator("#review")).to_be_visible()
        deadline = time.monotonic() + 10
        while not held and time.monotonic() < deadline:
            page.wait_for_timeout(50)
        assert held, "actual event response not held"
        page.get_by_role("button", name="Lock review").click()
        before = len(urls)
        route, body = held[0]
        route.fulfill(status=200, content_type="application/json", body=body)
        complete_action(page)
        assert len(urls) == before, "locked callback issued a new request"
        expect(page.locator("#workspace")).to_be_hidden()
        expect(page.get_by_label("Local reviewer token")).to_be_focused()
        expect(page.locator("#approve")).to_be_disabled()
        report.update(
            injected="delay_actual_event_response_until_lock", late_requests=urls[before:]
        )
        finish(directory, report, page)
        assert len(report["ledger"]["runs"]) == 1 and len(report["ledger"]["saves"]) == 0


def test_lost_save_acknowledgment_recovers_same_single_result(
    case: tuple[Path, dict[str, Any]],
) -> None:
    directory, report = case
    with installed_reviewer(directory) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        view = cast(dict[str, Any], submit(page, "GPU-A", live=False))
        committed: list[dict[str, Any]] = []

        def dropped(route: Route) -> None:
            response = route.fetch()
            assert response.status == 200
            committed.append(response.json())
            route.abort("failed")

        page.route("**/api/review", dropped)
        capture_actions(page)
        page.get_by_role("button", name="Approve exact brief", exact=True).click()
        complete_action(page)
        expect(page.locator("#error")).to_be_visible()
        assert len(committed) == 1
        saved = committed[0]["saved"]["saved_id"]
        assert len(cast(dict[str, Any], ledger(directory / "review.db", live=False))["saves"]) == 1
        page.unroute("**/api/review", dropped)
        page.get_by_role("button", name="Recover selected run").focus()
        page.get_by_role("button", name="Recover selected run").press("Enter")
        complete_action(page)
        expect(page.locator("#saved")).to_contain_text(saved)
        page.get_by_role("button", name="Approve exact brief", exact=True).focus()
        page.get_by_role("button", name="Approve exact brief", exact=True).press("Enter")
        complete_action(page)
        report.update(
            run_id=view["run_id"],
            saved_id=saved,
            injected="drop_after_actual_durable_save",
            explicit_human_repeat=True,
        )
        finish(directory, report, page)
        assert len(report["ledger"]["saves"]) == 1
        assert sum(e["kind"] == "tool_started" for e in report["ledger"]["events"]) == 2


def test_source_failure_keeps_exact_review_and_prior_source(
    case: tuple[Path, dict[str, Any]],
) -> None:
    directory, report = case
    with installed_reviewer(directory) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        view = cast(dict[str, Any], submit(page, "GPU-A", live=False))
        capture_actions(page)
        page.locator("#evidence button").first.click()
        complete_action(page)
        original = page.locator("#source").inner_text()
        assert original
        page.route("**/api/source?*", reject_transport)
        page.locator("#evidence button").first.focus()
        page.locator("#evidence button").first.press("Enter")
        complete_action(page)
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#identity")).to_contain_text(view["brief"]["brief_id"])
        expect(page.locator("#approve")).to_be_enabled()
        assert page.locator("#source").inner_text() == original
        report.update(
            run_id=view["run_id"], injected="source503_before_backend", prior_source_retained=True
        )
        finish(directory, report, page)
        assert len(report["ledger"]["saves"]) == 0


def test_failed_selected_run_read_is_keyboard_recoverable(
    case: tuple[Path, dict[str, Any]],
) -> None:
    directory, report = case
    with installed_reviewer(directory) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        view = cast(dict[str, Any], submit(page, "GPU-A", live=False))
        page.route("**/api/run?*", reject_transport)
        capture_actions(page)
        page.locator("#runs button").first.focus()
        page.locator("#runs button").first.press("Enter")
        complete_action(page)
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#approve")).to_be_disabled()
        page.get_by_role("button", name="Recover selected run").focus()
        page.get_by_role("button", name="Recover selected run").press("Enter")
        complete_action(page)
        expect(page.locator("#identity")).to_contain_text(view["brief"]["brief_id"])
        expect(page.locator("#review-title")).to_be_focused()
        report.update(
            run_id=view["run_id"],
            injected="run_read503_before_backend",
            recovered_brief_id=view["brief"]["brief_id"],
        )
        finish(directory, report, page)
        assert len(report["ledger"]["saves"]) == 0
