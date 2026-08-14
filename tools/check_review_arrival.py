"""Require an advisory Copilot review for the pull request's current commit."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


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
    with urlopen(request) as response:
        reviews = json.load(response)
    accepted = {
        "copilot-pull-request-reviewer",
        "copilot-pull-request-reviewer[bot]",
    }
    matching = [
        review
        for review in reviews
        if review.get("user", {}).get("login") in accepted and review.get("commit_id") == head_sha
    ]
    if not matching:
        print("Copilot review has not arrived for the current pull-request commit.")
        return 1
    print("advisory Copilot review arrived for the current commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
