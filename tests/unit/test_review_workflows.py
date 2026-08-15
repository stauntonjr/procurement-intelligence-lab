"""Lock the fork trust boundary in pull-request review workflows."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAME_REPOSITORY = "github.event.pull_request.head.repo.full_name == github.repository"


def workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_review_arrival_runs_only_for_ready_same_repository_pull_requests() -> None:
    content = workflow("review-arrival.yml")

    assert "pull_request_target" not in content
    assert SAME_REPOSITORY in content
    assert "github.event.pull_request.draft == false" in content
    assert "pull-requests: read" in content
    assert "GITHUB_TOKEN: ${{ github.token }}" in content


def test_advisory_gemini_review_cannot_run_for_forks_or_dependabot() -> None:
    content = workflow("gemini-review.yml")

    assert "pull_request_target" not in content
    assert SAME_REPOSITORY in content
    assert "github.actor != 'dependabot[bot]'" in content
    assert "gemini_api_key: ${{ secrets.GEMINI_API_KEY }}" in content
    assert "GITHUB_TOKEN: ''" in content
