"""Lock the deterministic-only pull-request review workflow policy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pull_request_workflows() -> list[Path]:
    return [
        path
        for path in (ROOT / ".github" / "workflows").glob("*.yml")
        if "pull_request:" in path.read_text(encoding="utf-8")
    ]


def workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_pull_request_workflows_are_deterministic_and_secret_free() -> None:
    """AI review is advisory and must never block or consume PR-triggered quota."""
    contents = [path.read_text(encoding="utf-8") for path in pull_request_workflows()]

    assert contents
    for content in contents:
        assert "pull_request_target" not in content
        assert "run-gemini-cli" not in content
        assert "gemini_api_key" not in content
        assert "check_review_arrival.py" not in content


def test_pr_contract_reads_the_current_pull_request_body() -> None:
    content = workflow("pr-contract.yml")

    assert "pull-requests: read" in content
    assert 'gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER"' in content
    assert "github.event.pull_request.body" not in content
    assert "PR_AUTHOR_LOGIN: ${{ github.event.pull_request.user.login }}" in content
    assert "PR_HEAD_REF: ${{ github.event.pull_request.head.ref }}" in content
    assert "PR_BASE_REF: ${{ github.event.pull_request.base.ref }}" in content
    assert "PR_COMMIT_AUTHORS_PATH: ${{ runner.temp }}/pr-commit-authors.txt" in content
    assert "pulls/$PR_NUMBER/commits?per_page=100" in content
    assert '.[].author.login // ""' in content
