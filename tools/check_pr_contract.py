"""Fail pull requests that omit the repository's executable-specification fields."""

from __future__ import annotations

import os
import re

REQUIRED_HEADINGS = (
    "Summary",
    "Why",
    "Milestone and issue",
    "Semantic contract",
    "Scenario coverage",
    "Evidence / validation",
    "Review disposition",
)
REQUIRED_VALUES = (
    "Primary milestone",
    "Linked issue",
    "Authoritative inputs",
    "Authoritative output",
    "Scope/as-of rule",
    "Governing policy",
    "Evidence retained",
    "Typed failure behavior",
)


def validate(body: str) -> tuple[str, ...]:
    errors: list[str] = []
    for heading in REQUIRED_HEADINGS:
        if not re.search(rf"(?m)^## {re.escape(heading)}\s*$", body):
            errors.append(f"missing heading: {heading}")
    for label in REQUIRED_VALUES:
        match = re.search(rf"(?m)^- {re.escape(label)}:\s*(.*)$", body)
        if match is None or not match.group(1).strip():
            errors.append(f"missing value: {label}")
    if not re.search(r"(?m)^\| .+ \| (?:yes|no|n/a) \| .+ \|\s*$", body, re.IGNORECASE):
        errors.append("scenario table must contain at least one completed yes/no/n/a row")
    return tuple(errors)


def main() -> int:
    body = os.environ.get("PR_BODY", "")
    errors = validate(body)
    if errors:
        print("Pull request contract is incomplete:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("pull request contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
