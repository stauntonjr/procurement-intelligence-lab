"""Lock the fork trust boundary in pull-request review workflows."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAME_REPOSITORY = "github.event.pull_request.head.repo.full_name == github.repository"


def workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def has_yaml_key(content: str, key: str) -> bool:
    prefix = f"{key}:"
    return any(line.lstrip().startswith(prefix) for line in content.splitlines())


def assert_if_condition_contains(content: str, expected: str) -> None:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("if:"):
            window = "\n".join(lines[i : i + 12])
            assert expected in window
            return
    raise AssertionError("workflow does not define an if: condition")


def test_review_arrival_runs_only_for_ready_same_repository_pull_requests() -> None:
    content = workflow("review-arrival.yml")

    assert not has_yaml_key(content, "pull_request_target")
    assert_if_condition_contains(content, SAME_REPOSITORY)
    assert_if_condition_contains(content, "github.event.pull_request.draft == false")
    assert "pull-requests: read" in content
    assert "pull-requests: write" not in content
    assert "permissions: write-all" not in content
    assert "GITHUB_TOKEN: ${{ github.token }}" in content


def test_advisory_gemini_review_cannot_run_for_forks_or_dependabot() -> None:
    content = workflow("gemini-review.yml")

    assert not has_yaml_key(content, "pull_request_target")
    assert_if_condition_contains(content, SAME_REPOSITORY)
    assert_if_condition_contains(content, "github.actor != 'dependabot[bot]'")
    assert "pull-requests: write" in content
    assert "contents: write" not in content
    assert "permissions: write-all" not in content
    assert "gemini_api_key: ${{ secrets.GEMINI_API_KEY }}" in content
    assert "GITHUB_TOKEN: ''" in content
