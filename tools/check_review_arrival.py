"""Require an advisory Copilot review for the pull request's current commit."""

from __future__ import annotations

import json
import os
import time
from urllib.request import Request, urlopen

HTTP_TIMEOUT_SECONDS = 10


def main() -> int:
    repository = os.environ["GITHUB_REPOSITORY"]
    pull_request = os.environ["PR_NUMBER"]
    head_sha = os.environ["PR_HEAD_SHA"]
    token = os.environ["GITHUB_TOKEN"]
    request = Request(
        f"https://api.github.com/repos/{repository}/pulls/{pull_request}/reviews?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    wait_seconds = max(float(os.environ.get("REVIEW_WAIT_SECONDS", "0")), 0)
    poll_seconds = max(float(os.environ.get("REVIEW_POLL_SECONDS", "15")), 1)
    deadline = time.monotonic() + wait_seconds
    accepted = {
        "copilot-pull-request-reviewer",
        "copilot-pull-request-reviewer[bot]",
    }
    while True:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            reviews = json.load(response)
        matching = [
            review
            for review in reviews
            if review.get("user", {}).get("login") in accepted
            and review.get("commit_id") == head_sha
        ]
        if matching:
            print("advisory Copilot review arrived for the current commit")
            return 0
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("Copilot review has not arrived for the current pull-request commit.")
            return 1
        time.sleep(min(poll_seconds, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
