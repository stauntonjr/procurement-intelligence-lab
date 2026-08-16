"""Run the lockfile-pinned roadmap reviewer and validate its public report contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADINGS = (
    "Current state",
    "Drift or conflicts",
    "Missing durable intake",
    "Recommended human decisions",
)


class RoadmapReviewError(RuntimeError):
    """The advisory CLI did not produce a valid roadmap review."""


def parse_report(stdout: str) -> str:
    try:
        payload: object = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RoadmapReviewError("Gemini CLI stdout must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise RoadmapReviewError("Gemini CLI stdout must be a JSON object")
    response = cast(dict[str, object], payload).get("response")
    if not isinstance(response, str) or not response.strip():
        raise RoadmapReviewError("Gemini CLI JSON must contain a non-empty response")
    headings = tuple(re.findall(r"(?m)^## ([^\r\n]+)\s*$", response))
    if headings != REQUIRED_HEADINGS:
        raise RoadmapReviewError(
            "roadmap review must contain exactly the required headings in order"
        )
    return response


def _write_output(path: Path, name: str, value: str) -> None:
    delimiter = "ROADMAP_REVIEW_EOF"
    while delimiter in value:
        delimiter += "_"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def run_review(gemini_bin: Path, prompt_path: Path, github_output: Path) -> int:
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
        completed = subprocess.run(
            [str(gemini_bin), "--yolo", "--prompt", prompt, "--output-format", "json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        if completed.returncode != 0:
            raise RoadmapReviewError(
                f"Gemini CLI exited with status {completed.returncode}; inspect step logs"
            )
        report = parse_report(completed.stdout)
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
        "--gemini-bin",
        type=Path,
        default=Path(".github/roadmap-steward/node_modules/.bin/gemini"),
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=Path(".github/roadmap-steward/prompt.md"),
    )
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    github_output = args.github_output
    if github_output is None:
        output_value = os.environ.get("GITHUB_OUTPUT")
        if not output_value:
            parser.error("--github-output or GITHUB_OUTPUT is required")
        github_output = Path(output_value)
    return run_review(args.gemini_bin, args.prompt_file, github_output)


if __name__ == "__main__":
    raise SystemExit(main())
