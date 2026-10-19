"""Produce a read-only advisory review with one bounded Gemini API request."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gemini-3.8-flash"
REQUIRED_HEADINGS = (
    "Current state",
    "Drift or conflicts",
    "Missing durable intake",
    "Recommended human decisions",
)
SNAPSHOT_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/project/handoff.md",
    "docs/development/milestone-map.md",
    "docs/development/github-plan.md",
    "docs/development/roadmap-stewardship.md",
    ".roadmap-audit/issues.json",
    ".roadmap-audit/pull-requests.json",
    ".roadmap-audit/milestones.json",
)


class RoadmapReviewError(RuntimeError):
    """The advisory request did not produce a valid roadmap review."""


def parse_report(stdout: str) -> str:
    try:
        payload: object = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RoadmapReviewError("review response must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise RoadmapReviewError("review response must be a JSON object")
    response = cast(dict[str, object], payload).get("response")
    if not isinstance(response, str) or not response.strip():
        raise RoadmapReviewError("review JSON must contain a non-empty response")
    matches = tuple(re.finditer(r"(?m)^## ([^\r\n]+)[ \t]*$", response))
    if tuple(match.group(1).strip() for match in matches) != REQUIRED_HEADINGS:
        raise RoadmapReviewError(
            "roadmap review must contain exactly the required headings in order"
        )
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(response)
        if not response[match.end() : end].strip():
            raise RoadmapReviewError(
                "roadmap review requires a non-empty section under each heading"
            )
    return response


def build_snapshot(root: Path, paths: tuple[str, ...], *, max_bytes: int = 2_000_000) -> str:
    """Read only named inputs; reject incomplete/oversized evidence rather than truncating it."""
    sources: dict[str, str] = {}
    for name in sorted(set(paths)):
        path = root / name
        if not path.is_file():
            raise RoadmapReviewError(f"snapshot input missing: {name}")
        sources[name] = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            try:
                json.loads(sources[name])
            except json.JSONDecodeError as exc:
                raise RoadmapReviewError(f"snapshot input is not valid JSON: {name}") from exc
    snapshot = json.dumps(sources, ensure_ascii=False, sort_keys=True)
    if len(snapshot.encode()) > max_bytes:
        raise RoadmapReviewError("snapshot exceeds size limit; narrow the declared audit scope")
    return snapshot


def parse_provider_response(payload: object) -> str:
    try:
        data = cast(dict[str, object], payload)
        candidates = cast(list[dict[str, object]], data["candidates"])
        if len(candidates) != 1 or candidates[0]["finishReason"] != "STOP":
            raise RoadmapReviewError("Gemini response is missing, blocked or truncated")
        content = cast(dict[str, object], candidates[0]["content"])
        parts = cast(list[dict[str, object]], content["parts"])
        text = "".join(
            str(part["text"]) for part in parts if "text" in part and not part.get("thought")
        )
        return parse_report(text)
    except (KeyError, TypeError, AttributeError) as exc:
        raise RoadmapReviewError("Gemini response has an invalid envelope") from exc


def generate_report(prompt: str, snapshot: str, api_key: str) -> str:
    if not api_key.strip():
        raise RoadmapReviewError(
            "GEMINI_API_KEY is missing; configure the Actions repository secret"
        )
    body = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"role": "user", "parts": [{"text": snapshot}]}],
        "generationConfig": {
            "maxOutputTokens": 16384,
            "thinkingConfig": {"thinkingLevel": "LOW"},
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {"response": {"type": "STRING"}},
                "required": ["response"],
            },
        },
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload: object = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        reason = "quota/rate limit unavailable" if exc.code == 429 else "provider request rejected"
        raise RoadmapReviewError(f"Gemini HTTP {exc.code}: {reason}; no automatic retry") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RoadmapReviewError("Gemini transport timeout/failure or malformed response") from exc
    return parse_provider_response(payload)


def _write_output(path: Path, name: str, value: str) -> None:
    delimiter = "ROADMAP_REVIEW_EOF"
    while delimiter in value:
        delimiter += "_"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def run_review(prompt_path: Path, github_output: Path, report_file: Path | None = None) -> int:
    try:
        if report_file is not None:
            report = parse_report(report_file.read_text(encoding="utf-8"))
        else:
            paths = SNAPSHOT_FILES + tuple(
                str(path.relative_to(ROOT))
                for pattern in ("docs/adr/*.md", "docs/architecture/*.md")
                for path in sorted(ROOT.glob(pattern))
            )
            snapshot = build_snapshot(ROOT, paths)
            digest = hashlib.sha256(snapshot.encode()).hexdigest()
            print(
                f"Roadmap model={MODEL}; snapshot_sha256={digest}; files={len(paths)}; requests=1"
            )
            report = generate_report(
                prompt_path.read_text(encoding="utf-8"),
                snapshot,
                os.environ.get("GEMINI_API_KEY", ""),
            )
    except (OSError, UnicodeError, RoadmapReviewError) as exc:
        message = str(exc)
        _write_output(github_output, "roadmap_error", message)
        print(f"roadmap review failed: {message}", file=sys.stderr)
        return 1
    _write_output(github_output, "roadmap_report", report)
    print("roadmap review produced a valid advisory report")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt-file", type=Path, default=Path(".github/roadmap-steward/prompt.md")
    )
    parser.add_argument(
        "--report-file", type=Path, help="Validate an existing provider-neutral report"
    )
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    github_output = args.github_output
    if github_output is None:
        output_value = os.environ.get("GITHUB_OUTPUT")
        if not output_value:
            parser.error("--github-output or GITHUB_OUTPUT is required")
        github_output = Path(output_value)
    return run_review(args.prompt_file, github_output, args.report_file)


if __name__ == "__main__":
    raise SystemExit(main())
