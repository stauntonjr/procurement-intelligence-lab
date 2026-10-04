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
    directory: Path, *, live: bool = False, port: int = 0
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
        "atlas",
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
