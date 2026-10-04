"""Opt-in real Chromium checks against a clean installed reviewer CLI.

PIL_BROWSER_PYTHON names the installed wheel Python. Browser binaries must already
be installed (or PIL_BROWSER_EXECUTABLE names one). No traces/HAR or credential logs.
Normal CI does not launch a browser or call inference.
"""

import os
import secrets
import select
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from playwright.sync_api import Error, Page, expect, sync_playwright

pytestmark = pytest.mark.skipif(
    not os.environ.get("PIL_BROWSER_PYTHON"), reason="explicit installed-browser opt-in required"
)


@dataclass
class InstalledReviewer:
    process: subprocess.Popen[str]
    origin: str
    token: str = field(repr=False)


@contextmanager
def installed_reviewer(
    directory: Path,
    *,
    live: bool = False,
    port: int = 0,
    sources: str = "corpus",
    project: str = "atlas",
) -> Generator[InstalledReviewer]:
    directory.mkdir(parents=True, exist_ok=True)
    token_file = directory / "token"
    if not token_file.exists():
        token_file.touch(mode=0o600)
        token_file.write_text(secrets.token_urlsafe(48))
    command = [
        str(Path(os.environ["PIL_BROWSER_PYTHON"]).absolute()),
        "-m",
        "procurement_intelligence_lab.interfaces.review_web",
        "--database",
        str(directory / "review.db"),
        "--project",
        project,
        "--sources",
        sources,
        "--token-file",
        str(token_file),
        "--port",
        str(port),
    ]
    if live:
        command.extend(["--model-endpoint", "http://127.0.0.1:8000/v1"])
    process = subprocess.Popen(
        command, cwd="/tmp", text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    try:
        assert process.stdout is not None
        assert select.select([process.stdout], [], [], 15)[0], "installed server startup timeout"
        line = process.stdout.readline().strip()
        origin = line.rsplit(" ", 1)[-1]
        assert origin.startswith("http://127.0.0.1:"), "installed server unavailable"
        yield InstalledReviewer(process, origin, token_file.read_text())
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()


@contextmanager
def chromium_page() -> Generator[Page]:
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(
            headless=True, executable_path=os.environ.get("PIL_BROWSER_EXECUTABLE")
        )
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 1000})
            yield context.new_page()
        finally:
            browser.close()


def sign_in(page: Page, reviewer: InstalledReviewer) -> None:
    # Action/expectation errors can include credential values. Suppress all sign-in diagnostics.
    try:
        page.goto(reviewer.origin)
        password = page.get_by_label("Local reviewer token")
        expect(password).to_be_visible()
        password.fill(reviewer.token)
        password.press("Enter")
        expect(page.locator("#workspace")).to_be_visible()
        expect(password).to_have_value("")
    except (Error, AssertionError):
        raise AssertionError("Private authentication or credential erasure failed") from None


@pytest.mark.parametrize("live", [False, True], ids=["fixture", "live-page-no-inference"])
def test_browser_sign_in_moves_keyboard_focus_to_request(tmp_path: Path, live: bool) -> None:
    with installed_reviewer(tmp_path, live=live) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        request = page.get_by_label("Question" if live else "Canonical item", exact=True)
        expect(request).to_be_focused()
        assert page.evaluate("localStorage.length + sessionStorage.length") == 0
        assert not page.context.cookies()
        assert reviewer.token not in page.url


def contrast(first: str, second: str) -> float:
    """WCAG relative luminance for Chromium's opaque computed RGB colors."""
    import re

    def luminance(color: str) -> float:
        values = [int(value) / 255 for value in re.findall(r"\d+", color)]
        assert len(values) == 3, "opaque computed RGB required"
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return sum(weight * v for weight, v in zip((0.2126, 0.7152, 0.0722), linear, strict=True))

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_browser_focus_indicator_has_adjacent_contrast(tmp_path: Path) -> None:
    with installed_reviewer(tmp_path) as reviewer, chromium_page() as page:
        sign_in(page, reviewer)
        request = page.get_by_label("Canonical item", exact=True)
        request.focus()
        colors = request.evaluate(
            "e=>({outline:getComputedStyle(e).outlineColor,"
            "background:getComputedStyle(e.closest('section')).backgroundColor})"
        )
        ratio = contrast(colors["outline"], colors["background"])
        assert ratio >= 3, f"Visible focus must contrast with its adjacent background: {ratio}"


def submit(page: Page, value: str, *, live: bool) -> dict[str, object]:
    from typing import cast

    label = "Question" if live else "Canonical item"
    page.get_by_label(label, exact=True).fill(value)
    page.get_by_label("As of (ISO 8601 with timezone)").fill("2026-10-01T00:00:00Z")
    with page.expect_response("**/api/ask" if live else "**/api/start") as response:
        page.get_by_label(label, exact=True).press("Enter")
    assert response.value.status == 200
    expect(page.get_by_role("button", name="Investigate and draft")).to_be_enabled()
    return cast(dict[str, object], response.value.json())


def review(page: Page, decision: str) -> dict[str, object]:
    from typing import cast

    button = page.get_by_role("button", name=f"{decision.capitalize()} exact brief", exact=True)
    expect(button).to_be_enabled()
    button.focus()
    with page.expect_response("**/api/review") as response:
        button.press("Enter")
    assert response.value.status == 200
    expect(page.get_by_role("button", name="Investigate and draft")).to_be_enabled()
    return cast(dict[str, object], response.value.json())


def ledger(database: Path, *, live: bool) -> dict[str, object]:
    import json
    import sqlite3

    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        calls = (
            [
                json.loads(row[0])
                for row in connection.execute("SELECT payload FROM interpretation_calls")
            ]
            if live
            else []
        )
        saves = [
            json.loads(row[0]) for row in connection.execute("SELECT payload FROM saved_briefs")
        ]
        runs = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM agent_runs")]
        events = [
            json.loads(row[0])
            for row in connection.execute("SELECT payload FROM agent_events ORDER BY sequence")
        ]
    return {"calls": calls, "saves": saves, "runs": runs, "events": events}


@pytest.mark.parametrize("live", [False, True], ids=["fixture-walkthrough", "live-walkthrough"])
def test_installed_browser_walkthrough(tmp_path: Path, live: bool) -> None:
    import json
    import re
    from contextlib import ExitStack
    from dataclasses import asdict
    from hashlib import sha256
    from typing import Any, cast
    from urllib.parse import urlsplit

    from procurement_intelligence_lab.interfaces.live_review import compose_live
    from procurement_intelligence_lab.interfaces.workflow import compose_services

    if live and os.environ.get("PIL_BROWSER_LIVE") != "1":
        pytest.skip("separate explicit live browser opt-in required")
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / "evals/operational_agents/browser-walkthrough-v1.json"
    manifest = json.loads(manifest_path.read_text())
    output = Path(os.environ["PIL_BROWSER_OUTPUT"]).absolute() / ("live" if live else "fixture")
    assert not output.exists(), "fresh output directory required; never overwrite evidence"
    output.mkdir(parents=True)
    database = output / "review.db"
    versions = asdict(
        (compose_live(database) if live else compose_services(database)).runs.versions
    )
    # Verify the installed composition, without putting checkout paths into the server process.
    probe = (
        "import json,tempfile; from pathlib import Path; from dataclasses import asdict; "
        f"from procurement_intelligence_lab.interfaces.{'live_review' if live else 'workflow'} "
        f"import {'compose_live' if live else 'compose_services'} as compose; "
        'print(json.dumps(asdict(compose(Path(tempfile.mkdtemp())/"probe.db").runs.versions)))'
    )
    installed = json.loads(
        subprocess.check_output(
            [str(Path(os.environ["PIL_BROWSER_PYTHON"]).absolute()), "-c", probe],
            cwd="/tmp",
            text=True,
        )
    )
    assert installed == versions, "installed wheel differs from frozen checkout"
    cases = [
        dict(case, id=f"{case['id']}-r{repetition}")
        for repetition in range(1, 4 if live else 2)
        for case in manifest["scenarios"]
    ]
    if live:
        cases.extend(dict(case, abstention=True) for case in manifest["controls"])
        cases.append(dict(manifest["injection"], id="injected-approval", injection=True))
    report: dict[str, Any] = {
        "schema_version": 1,
        "execution_kind": "live" if live else "fixture",
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "versions": versions,
        "limits": manifest["limits"],
        "application_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "runs": [{"id": case["id"], "outcome": "unknown"} for case in cases],
        "screenshots": [],
        "acceptance": "not_ready",
    }

    def retain() -> None:
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    retain()
    source_checks = 0
    js_errors: list[str] = []
    try:
        with chromium_page() as page, ExitStack() as servers:
            report["browser"] = page.context.browser.version if page.context.browser else "unknown"
            page.on("pageerror", lambda _: js_errors.append("javascript_runtime_error"))
            reviewer = servers.enter_context(installed_reviewer(output, live=live))
            requests: list[str] = []
            page.on("request", lambda request: requests.append(request.url))
            sign_in(page, reviewer)
            expect(
                page.get_by_label("Question" if live else "Canonical item", exact=True)
            ).to_be_focused()
            for case, record in zip(cases, report["runs"], strict=True):
                result = cast(
                    dict[str, Any],
                    submit(page, case["question"] if live else case["item"], live=live),
                )
                if live:
                    call = result["interpretation"]
                    record["interpretation"] = call
                    assert call["status"] == case.get("expected", "investigate")
                    record["run_id"] = call["run_id"]
                    if case.get("abstention"):
                        assert result["workflow"] is None
                        expect(page.locator("#review")).to_be_hidden()
                        expect(page.locator("#approve")).to_be_disabled()
                        expect(page.locator("#interpretation")).to_contain_text(call["status"])
                        with page.expect_response("**/api/recover") as response:
                            page.get_by_role("button", name="Recover selected run").click()
                        assert response.value.json() == result
                        record.update(outcome="pass", disposition="no_brief_no_tools_no_save")
                        retain()
                        continue
                    view = result["workflow"]
                else:
                    view = result
                record["run_id"] = view["run_id"]
                facts = json.loads(view["brief"]["content_json"])
                if not case.get("injection"):
                    assert {
                        key: facts[key]
                        for key in ("status", "reason", "required_quantity", "ordered_quantity")
                    } == {
                        key: case[key]
                        for key in ("status", "reason", "required_quantity", "ordered_quantity")
                    }
                assert view["saved"] is None and view["status"] == "awaiting_review"
                assert view["execution_kind"] == report["execution_kind"]
                expect(page.locator("#review-title")).to_be_focused()
                expect(page.locator("#outcome")).to_contain_text(
                    "Required: " + (facts["required_quantity"] or "unresolved")
                )
                expect(page.locator("#outcome")).to_contain_text(
                    "Assessed ordered: " + (facts["ordered_quantity"] or "not established")
                )
                expect(page.locator("#events")).to_contain_text("tool_succeeded")
                record["facts"] = {
                    key: facts[key]
                    for key in ("status", "reason", "required_quantity", "ordered_quantity")
                }
                for index, ref in enumerate(facts["evidence"]):
                    with page.expect_response("**/api/source?*") as response:
                        button = page.locator("#evidence button").nth(index)
                        button.focus()
                        button.press("Enter")
                    assert response.value.status == 200
                    source = response.value.json()
                    assert source["evidence"]["evidence_id"] == ref["evidence_id"]
                    if "cells" in source:
                        expect(page.locator("#source td")).to_have_text(source["cells"])
                        expected = [
                            source["cells"][ord(c) - ord("A")]
                            for c in source["highlighted_columns"]
                        ]
                        expect(page.locator("#source td.highlight")).to_have_text(expected)
                    else:
                        expect(page.locator("#source pre")).to_have_text(
                            json.dumps(source["authority"], indent=2)
                        )
                    source_checks += 1
                record["source_count"] = len(facts["evidence"])
                assert record["source_count"] > 0
                if case["id"] == "mismatch-r1":
                    ratios: dict[str, float] = {}
                    for selector in ("#outcome", "#approve", "#workspace .muted"):
                        colors = page.locator(selector).first.evaluate(
                            "e=>({text:getComputedStyle(e).color,background:"
                            "getComputedStyle(e.matches('.muted')?e.closest('section'):e).backgroundColor})"
                        )
                        ratios[selector] = contrast(colors["text"], colors["background"])
                    assert min(ratios.values()) >= 4.5
                    report["selected_text_contrast"] = ratios
                    for width, name in [(1280, "wide"), (375, "narrow")]:
                        page.set_viewport_size({"width": width, "height": 1000})
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        ), "page reflow overflow"
                        assert page.get_by_label("Local reviewer token").input_value() == ""
                        screenshot = output / f"mismatch-{name}.png"
                        page.screenshot(path=str(screenshot), full_page=True)
                        report["screenshots"].append(
                            {
                                "path": screenshot.name,
                                "sha256": sha256(screenshot.read_bytes()).hexdigest(),
                            }
                        )
                    page.set_viewport_size({"width": 1280, "height": 1000})
                    # A real new installed server lifetime; no recalled model on discovery/recovery.
                    port = urlsplit(reviewer.origin).port
                    assert port is not None
                    servers.close()
                    reviewer = servers.enter_context(
                        installed_reviewer(output, live=live, port=port)
                    )
                    sign_in(page, reviewer)
                    with page.expect_response(
                        "**/api/interpretation?*" if live else "**/api/run?*"
                    ):
                        page.get_by_role(
                            "button", name=re.compile(re.escape(view["run_id"][:8]))
                        ).click()
                    expect(page.locator("#identity")).to_contain_text(view["brief"]["brief_id"])
                    with page.expect_response("**/api/recover") as response:
                        page.get_by_role("button", name="Recover selected run").click()
                    assert response.value.json() == result
                    record["process_restart_recovered"] = True

                    # Alter the actual browser review request once, leaving authority server-owned.
                    def altered(route: Any) -> None:
                        body = route.request.post_data_json
                        route.continue_(post_data=json.dumps(body | {"digest": "0" * 64}))

                    page.route("**/api/review", altered)
                    with page.expect_response("**/api/review") as response:
                        page.get_by_role("button", name="Approve exact brief").click()
                    assert response.value.status == 409
                    page.unroute("**/api/review", altered)
                    expect(page.locator("#error")).to_be_visible()
                    record["altered_digest_rejected"] = True
                decision = (
                    "reject" if case["id"] in ("unresolved-r1", "injected-approval") else "approve"
                )
                reviewed = cast(dict[str, Any], review(page, decision))
                if decision == "approve":
                    assert reviewed["status"] == "completed"
                    saved = reviewed["saved"]
                    expect(page.locator("#saved")).to_contain_text(saved["saved_id"])
                    assert review(page, decision) == reviewed
                    record["saved_id"] = saved["saved_id"]
                else:
                    assert reviewed["status"] == "rejected" and reviewed["saved"] is None
                    expect(page.locator("#approve")).to_be_disabled()
                record.update(outcome="pass", decision=decision, digest=view["brief"]["digest"])
                retain()
            page.get_by_role("button", name="Lock review").click()
            expect(page.get_by_label("Local reviewer token")).to_be_focused()
            expect(page.locator("#workspace")).to_be_hidden()
            assert page.evaluate("localStorage.length + sessionStorage.length") == 0
            assert not page.context.cookies()
            assert all(
                url.startswith(reviewer.origin) and reviewer.token not in url for url in requests
            )
            sign_in(page, reviewer)
            page.reload()
            expect(page.locator("#workspace")).to_be_hidden()
            expect(page.get_by_label("Local reviewer token")).to_have_value("")
            sign_in(page, reviewer)
            report["reload_requires_sign_in"] = True
            assert not js_errors
            actual = cast(dict[str, Any], ledger(database, live=live))
            report["ledger"] = actual
            assert len(actual["calls"]) == (14 if live else 0)
            assert len(actual["saves"]) == (8 if live else 2)
            calls = {c["run_id"]: c for c in actual["calls"]}
            saves = {s["run_id"]: s for s in actual["saves"]}
            assert len(actual["runs"]) == len(cases)
            runs = {r["run_id"]: r for r in actual["runs"]}
            for case, record in zip(cases, report["runs"], strict=True):
                run = runs[record["run_id"]]
                assert run["versions"] == versions
                events = [e for e in actual["events"] if e["run_id"] == record["run_id"]]
                tools = [e for e in events if e["kind"] == "tool_started"]
                assert len(tools) == (0 if case.get("abstention") else 2)
                record["tool_started_count"] = len(tools)
                if live:
                    call = calls[record["run_id"]]
                    assert call == record["interpretation"]
                    assert call["question_hash"] == sha256(case["question"].encode()).hexdigest()
                if record.get("saved_id"):
                    assert saves[record["run_id"]]["saved_id"] == record["saved_id"]
                else:
                    assert record["run_id"] not in saves
            report.update(
                acceptance="bounded_browser_passed",
                source_checks=source_checks,
                keyboard=True,
                reflow_widths=[375, 1280],
                no_credential_storage=True,
                javascript_errors=js_errors,
            )
    finally:
        report["source_checks"] = source_checks
        retain()
        (output / "token").unlink(missing_ok=True)


@pytest.mark.parametrize("sources", ["showcase-a-order", "showcase-a-b-order", "showcase-a-only"])
def test_browser_original_source_labels_and_reflow(tmp_path: Path, sources: str) -> None:
    try:
        with (
            installed_reviewer(tmp_path, sources=sources, project="synthetic-project") as reviewer,
            chromium_page() as page,
        ):
            sign_in(page, reviewer)
            expect(page.get_by_label("Canonical item", exact=True)).to_be_focused()
            expect(page.get_by_label("As of (ISO 8601 with timezone)")).to_have_value(
                "2026-01-15T00:00:00Z"
            )
            with page.expect_response("**/api/start") as response:
                page.get_by_label("Canonical item", exact=True).press("Enter")
            assert response.value.status == 200
            expect(page.locator("#outcome")).to_contain_text("Order observation: ")
            expect(page.get_by_role("button", name="Investigate and draft")).to_be_enabled()
            page.set_viewport_size({"width": 375, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            with page.expect_response("**/api/source?*") as response:
                page.locator("#evidence button").first.click()
            assert response.value.status == 200
            expect(page.locator("#source td")).to_have_text(response.value.json()["cells"])
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        (tmp_path / "token").unlink(missing_ok=True)
