"""Record the explanatory deck followed by one live, evidence-focused review."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RecordingConfig:
    origin: str
    token_file: Path
    slides: Path
    output: Path
    live: bool = True
    recover_run_prefix: str | None = None
    width: int = 1440
    height: int = 900
    banner_height: int = 96
    typing_delay_ms: int = 45
    slide_pause_ms: int = 2400
    read_pause_ms: int = 800


def ordered_slides(directory: Path) -> list[Path]:
    def number(path: Path) -> int:
        return int(path.stem.removeprefix("slide-"))

    return sorted(directory.glob("slide-*.png"), key=number)


def build_banner(**parts: str) -> dict[str, str]:
    expected = ("who", "what", "why", "how", "when")
    for key in expected:
        if not str(parts.get(key, "")).strip():
            raise ValueError(f"banner field {key} must be nonempty")
    return {key: str(parts[key]).strip() for key in expected}


def build_typing_events(text: str, *, delay_ms: int) -> list[dict[str, Any]]:
    return [{"kind": "key", "text": character, "delay_ms": delay_ms} for character in text]


def extract_unresolved_facts(payload: dict[str, Any]) -> dict[str, Any]:
    """Bind the recording narrative to the exact governed finding returned."""
    try:
        view = payload.get("workflow", payload)
        facts = json.loads(view["brief"]["content_json"])
        evidence_ids = [ref["evidence_id"] for ref in facts["evidence"]]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("reviewer did not return a readable governed finding") from error
    if (
        facts.get("status") != "not_assessed"
        or facts.get("reason") != "unresolved_requirement"
        or facts.get("required_quantity") is not None
    ):
        raise ValueError("recording requires an unresolved_requirement finding")
    if len(evidence_ids) < 3 or len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("unresolved requirement must retain distinct competing evidence")
    return {
        "status": facts["status"],
        "reason": facts["reason"],
        "required_quantity": facts["required_quantity"],
        "ordered_quantity": facts.get("ordered_quantity"),
        "evidence_ids": evidence_ids,
    }


def extract_reconciliation_result(
    payload: dict[str, Any], *, historical: dict[str, Any], original_cutoff: str
) -> dict[str, Any]:
    try:
        decision = payload["decision"]
        current = payload["current_assessment"]
        scope = decision["scope"]
        effective_at = datetime.fromisoformat(decision["effective_at"])
        cutoff = datetime.fromisoformat(original_cutoff)
        candidate_ids = list(decision["candidate_claim_ids"])
        evidence_ids = list(decision["evidence_ids"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reviewer did not return a complete reconciliation result") from error
    if decision.get("outcome") != "select_governing_revision":
        raise ValueError("recording requires a governing revision selection")
    if not str(decision.get("rationale", "")).strip():
        raise ValueError("recording requires a reconciliation rationale")
    if decision.get("selected_claim_id") not in candidate_ids or len(candidate_ids) != 2:
        raise ValueError("recording requires one of exactly two retained candidates")
    if effective_at <= cutoff:
        raise ValueError("reconciliation must be prospective to the original cutoff")
    historical_evidence = list(historical.get("evidence_ids", []))
    if not evidence_ids or not set(evidence_ids).issubset(historical_evidence):
        raise ValueError("reconciliation evidence must remain linked to the historical assessment")
    if (
        historical.get("status") != "not_assessed"
        or historical.get("required_quantity") is not None
    ):
        raise ValueError("historical unresolved assessment was not retained")
    return {
        "decision_id": decision["decision_id"],
        "selected_claim_id": decision["selected_claim_id"],
        "candidate_claim_ids": candidate_ids,
        "rationale": decision["rationale"],
        "effective_at": decision["effective_at"],
        "exact_scope": {
            "tenant_id": scope["tenant_id"],
            "project_id": scope["project_id"],
            "site_id": scope["site_id"],
            "item": decision["subject_key"],
        },
        "historical_assessment_unchanged": True,
        "historical_assessment": historical,
        "current_assessment": current,
        "decision_evidence_ids": evidence_ids,
        "retained_evidence_ids": historical_evidence,
    }


def prepare_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"never overwrite recording evidence: {path}")
    path.mkdir(parents=True)


def public_report(config: RecordingConfig, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "origin": config.origin,
        "viewport": {"width": config.width, "height": config.height},
        "banner_height": config.banner_height,
        "typing_delay_ms": config.typing_delay_ms,
        "slide_count": len(ordered_slides(config.slides)),
        "result": result,
    }


def _banner_html(parts: dict[str, str]) -> str:
    labels = "".join(f"<span><b>{key.title()}:</b> {value}</span>" for key, value in parts.items())
    return f"<div id='story-banner'><em>{labels}</em></div>"


def _install_banner(page: Any, parts: dict[str, str], height: int) -> None:
    page.evaluate(
        """({html,height})=>{
          document.getElementById('story-banner')?.remove();
          document.body.insertAdjacentHTML('beforeend',html);
          document.body.style.paddingBottom=height+'px';
          const s=document.createElement('style'); s.id='story-style';
          s.textContent=`#story-banner{position:fixed;z-index:2147483647;left:0;right:0;bottom:0;
            min-height:${height}px;box-sizing:border-box;padding:13px 26px;background:#0d2339;
            color:#fff;border-top:4px solid #e1a11a;font:16px/1.35 Arial,sans-serif;
            display:grid;place-items:center}#story-banner em{display:flex;gap:10px 24px;
            flex-wrap:wrap;justify-content:center}#story-banner b{color:#f5c453}`;
          document.head.appendChild(s);
        }""",
        {"html": _banner_html(parts), "height": height},
    )


def _show_slide(page: Any, slide: Path) -> None:
    import base64

    encoded = base64.b64encode(slide.read_bytes()).decode()
    page.set_content(
        "<style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#0d2339}"
        "img{width:100%;height:100%;object-fit:contain;display:block}</style>"
        f"<img alt='Presentation slide' src='data:image/png;base64,{encoded}'>"
    )


def _type_visible(page: Any, label: str, text: str, delay_ms: int) -> None:
    field = page.get_by_label(label, exact=True)
    field.click()
    field.press("Control+A")
    field.press("Backspace")
    for event in build_typing_events(text, delay_ms=delay_ms):
        page.keyboard.type(event["text"], delay=event["delay_ms"])


def record(config: RecordingConfig, *, executable: str | None = None) -> dict[str, Any]:
    from playwright.sync_api import expect, sync_playwright

    slides = ordered_slides(config.slides)
    if len(slides) != 8:
        raise ValueError(f"expected eight slides, found {len(slides)}")
    prepare_output(config.output)
    token = config.token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("private reviewer credential is unavailable")
    video_dir = config.output / "video"
    video_dir.mkdir()
    item = "GPU-C"
    question = f"Compare the governing requirement revisions and recorded orders for {item}."
    request_label = "Procurement question" if config.live else "Item to review"
    request_value = question if config.live else item
    request_path = "**/api/ask" if config.live else "**/api/start"
    cutoff = "2026-10-01T00:00:00Z"
    banners = {
        "ask": build_banner(
            who="A buyer asks; the model only interprets intent",
            what=f"Investigate {item} requirements and orders",
            why="Conflicting revisions must not become false certainty",
            how="Type a bounded question and an as-of cutoff",
            when="Before deterministic evidence processing",
        ),
        "evidence": build_banner(
            who="The reviewer remains the decision owner",
            what="Inspect each cited original source",
            why="The answer must be traceable to admitted evidence",
            how="Select citations and highlight supporting cells",
            when="Before recording any reconciliation decision",
        ),
        "decision": build_banner(
            who="An authenticated human reviewer",
            what="Choose which displayed revision governs this item",
            why="Two eligible requirements disagree and policy abstained",
            how="Type a rationale and save an exact-scope prospective choice",
            when="Effective now; the earlier assessment remains unchanged",
        ),
    }
    started = time.monotonic()
    result: dict[str, Any] = {
        "scenario": f"{item} unresolved requirement",
        "execution_kind": "live" if config.live else "fixture",
        "acceptance": "not_ready",
    }
    video_path: Path | None = None
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True, executable_path=executable)
            context = browser.new_context(
                viewport={"width": config.width, "height": config.height},
                record_video_dir=str(video_dir),
                record_video_size={"width": config.width, "height": config.height},
            )
            page = context.new_page()
            for slide in slides:
                _show_slide(page, slide)
                page.wait_for_timeout(config.slide_pause_ms)

            # A full-frame privacy cover keeps the credential outside publishable frames.
            page.goto(config.origin)
            page.evaluate(
                """()=>{const c=document.createElement('div');c.id='privacy-cover';
                c.style='position:fixed;inset:0;z-index:2147483647;background:#0d2339;color:white;display:grid;place-items:center;font:700 30px Arial';
                c.textContent='Preparing the local reviewer…';document.body.appendChild(c)}"""
            )
            page.get_by_label("Local reviewer token").fill(token)
            page.get_by_label("Local reviewer token").press("Enter")
            expect(page.locator("#workspace")).to_be_visible(timeout=15_000)
            expect(page.get_by_label("Local reviewer token")).to_have_value("")
            page.locator("#privacy-cover").evaluate("e=>e.remove()")
            _install_banner(page, banners["ask"], config.banner_height)
            _type_visible(page, request_label, request_value, config.typing_delay_ms)
            _type_visible(page, "Evidence available through", cutoff, config.typing_delay_ms)
            if config.recover_run_prefix:
                target = page.locator("#runs button").filter(has_text=config.recover_run_prefix)
                expect(target).to_have_count(1)
                with page.expect_response("**/api/interpretation?*"):
                    target.click()
                with page.expect_response("**/api/recover", timeout=30_000) as response:
                    page.get_by_role("button", name="Recover selected run").click()
                result["execution"] = "persisted_run_recovery"
            else:
                with page.expect_response(request_path, timeout=90_000) as response:
                    page.get_by_label(request_label, exact=True).press("Enter")
                result["execution"] = "new_request"
            payload = response.value.json()
            if response.value.status != 200:
                raise AssertionError(
                    f"reviewer request failed: HTTP {response.value.status} "
                    f"code={payload.get('code', 'unknown')}"
                )
            governed_facts = extract_unresolved_facts(payload)
            view = payload.get("workflow", payload)
            facts = json.loads(view["brief"]["content_json"])
            candidates = [
                candidate for candidate in facts["governance_candidates"] if candidate["eligible"]
            ]
            if len(candidates) != 2:
                raise AssertionError("recording requires exactly two eligible displayed revisions")
            expect(page.locator("#review-title")).to_be_visible()
            page.wait_for_timeout(config.read_pause_ms)
            _install_banner(page, banners["evidence"], config.banner_height)
            buttons = page.locator("#evidence button")
            count = buttons.count()
            if count != len(governed_facts["evidence_ids"]):
                raise AssertionError("reviewer did not expose every governed evidence identity")
            inspected = [
                buttons.filter(has_text=candidate["revision_id"]).first for candidate in candidates
            ]
            highlighted_source_count = 0
            for button in inspected:
                with page.expect_response("**/api/source?*", timeout=30_000) as source_response:
                    button.focus()
                    button.press("Enter")
                if source_response.value.status != 200:
                    raise AssertionError("cited source could not be opened")
                expect(button).to_have_attribute("aria-pressed", "true")
                source_payload = source_response.value.json()
                if source_payload.get("cells"):
                    expect(page.locator("#source .source-note")).to_have_text(
                        "Highlighted cells support this assessment."
                    )
                    highlighted_source_count += 1
                page.wait_for_timeout(config.read_pause_ms)
            if highlighted_source_count < 2:
                raise AssertionError(
                    "both conflicting source documents must be shown with highlights"
                )
            expect(page.locator("#outcome")).to_contain_text("not_assessed")
            _install_banner(page, banners["decision"], config.banner_height)
            selected = candidates[1]
            choice = page.get_by_label(
                re.compile(f"Use revision {re.escape(selected['revision_id'])}")
            )
            choice.check()
            rationale = f"Revision {selected['revision_id']} governs {item} prospectively for this project and site."
            _type_visible(page, "Required rationale", rationale, config.typing_delay_ms)
            save = page.get_by_role(
                "button", name=f"Use revision {selected['revision_id']} prospectively", exact=True
            )
            expect(save).to_be_enabled()
            page.wait_for_timeout(config.read_pause_ms)
            with page.expect_response("**/api/reconcile", timeout=30_000) as reconciled:
                save.click()
            reconciled_payload = reconciled.value.json()
            if reconciled.value.status != 200:
                raise AssertionError("prospective reconciliation was not retained")
            reconciliation = extract_reconciliation_result(
                reconciled_payload, historical=governed_facts, original_cutoff=cutoff
            )
            result["decision"] = "select_governing_revision"
            result["reconciliation"] = reconciliation
            page.wait_for_timeout(config.read_pause_ms)
            body = page.locator("body").inner_text()
            for forbidden in (
                "Independent interview reference demo",
                "demo brief",
                "Investigate and draft",
                "Approve this finding",
                "Reject this finding",
            ):
                if forbidden in body:
                    raise AssertionError(f"forbidden reviewer copy is visible: {forbidden}")
            result.update(
                acceptance="pass",
                source_count=count,
                inspected_source_count=len(inspected),
                highlighted_source_count=highlighted_source_count,
                selected_source_highlighted=True,
                workflow_status=view["status"],
                governed_facts=governed_facts,
                credential_storage_empty=(
                    page.evaluate("localStorage.length + sessionStorage.length") == 0
                    and not context.cookies()
                    and token not in page.url
                ),
            )
            video = page.video
            page.close()
            context.close()
            video_path = Path(video.path())
            browser.close()
    finally:
        result["interaction_seconds"] = round(time.monotonic() - started, 3)
        report = public_report(config, result)
        serialized = json.dumps(report, indent=2) + "\n"
        if token in serialized:
            raise AssertionError("credential appeared in public report")
        (config.output / "report.json").write_text(serialized)

    assert video_path is not None
    destination = config.output / "walkthrough.webm"
    shutil.move(video_path, destination)
    result["video_sha256"] = sha256(destination.read_bytes()).hexdigest()
    probe = subprocess.run(
        ["gst-discoverer-1.0", str(destination)],
        check=True,
        text=True,
        capture_output=True,
    )
    discovered = probe.stdout
    duration = re.search(r"Duration: (\S+)", discovered)
    width = re.search(r"Width: (\d+)", discovered)
    height = re.search(r"Height: (\d+)", discovered)
    result["media"] = {
        "container": "webm" if "container #0: WebM" in discovered else "unknown",
        "codec": "vp8" if "video #1: VP8" in discovered else "unknown",
        "duration": duration.group(1) if duration else "unknown",
        "width": int(width.group(1)) if width else None,
        "height": int(height.group(1)) if height else None,
        "seekable": "Seekable: yes" in discovered,
    }
    (config.output / "report.json").write_text(
        json.dumps(public_report(config, result), indent=2) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8001")
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--recover-run-prefix")
    args = parser.parse_args()
    result = record(
        RecordingConfig(
            args.origin,
            args.token_file,
            args.slides,
            args.output,
            live=not args.fixture,
            recover_run_prefix=args.recover_run_prefix,
        ),
        executable=args.executable,
    )
    print(json.dumps({"acceptance": result["acceptance"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
