import io
import json
from collections.abc import Iterator
from urllib.error import URLError
from urllib.request import Request

from pytest import MonkeyPatch

from tools import check_review_arrival


def test_review_arrival_uses_bounded_http_timeout(monkeypatch: MonkeyPatch) -> None:
    head_sha = "a" * 40
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repository")
    monkeypatch.setenv("PR_NUMBER", "119")
    monkeypatch.setenv("PR_HEAD_SHA", head_sha)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    observed: dict[str, object] = {}

    def fake_urlopen(request: Request, *, timeout: float) -> io.BytesIO:
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        payload = [
            {
                "user": {"login": "copilot-pull-request-reviewer[bot]"},
                "commit_id": head_sha,
            }
        ]
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(check_review_arrival, "urlopen", fake_urlopen)

    assert check_review_arrival.main() == 0
    assert observed == {
        "url": "https://api.github.com/repos/owner/repository/pulls/119/reviews?per_page=100",
        "timeout": check_review_arrival.HTTP_TIMEOUT_SECONDS,
    }


def test_review_arrival_polls_within_bounded_wait(monkeypatch: MonkeyPatch) -> None:
    head_sha = "b" * 40
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repository")
    monkeypatch.setenv("PR_NUMBER", "120")
    monkeypatch.setenv("PR_HEAD_SHA", head_sha)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("REVIEW_WAIT_SECONDS", "10")
    monkeypatch.setenv("REVIEW_POLL_SECONDS", "2")
    empty_reviews: list[dict[str, object]] = []
    matching_reviews: list[dict[str, object]] = [
        {
            "user": {"login": "copilot-pull-request-reviewer[bot]"},
            "commit_id": head_sha,
        }
    ]
    payloads: Iterator[list[dict[str, object]]] = iter((empty_reviews, matching_reviews))
    monotonic_values = iter((100.0, 104.0))
    sleeps: list[float] = []

    def fake_urlopen(_request: Request, *, timeout: float) -> io.BytesIO:
        assert timeout == check_review_arrival.HTTP_TIMEOUT_SECONDS
        return io.BytesIO(json.dumps(next(payloads)).encode())

    monkeypatch.setattr(check_review_arrival, "urlopen", fake_urlopen)
    monkeypatch.setattr(check_review_arrival.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(check_review_arrival.time, "sleep", sleeps.append)

    assert check_review_arrival.main() == 0
    assert sleeps == [2.0]


def test_review_arrival_retries_transient_network_error(monkeypatch: MonkeyPatch) -> None:
    head_sha = "c" * 40
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repository")
    monkeypatch.setenv("PR_NUMBER", "121")
    monkeypatch.setenv("PR_HEAD_SHA", head_sha)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("REVIEW_WAIT_SECONDS", "10")
    monkeypatch.setenv("REVIEW_POLL_SECONDS", "2")
    matching_reviews: list[dict[str, object]] = [
        {
            "user": {"login": "copilot-pull-request-reviewer[bot]"},
            "commit_id": head_sha,
        }
    ]
    outcomes: Iterator[URLError | list[dict[str, object]]] = iter(
        (URLError("temporary DNS failure"), matching_reviews)
    )
    monotonic_values = iter((100.0, 104.0))

    def fake_urlopen(_request: Request, *, timeout: float) -> io.BytesIO:
        assert timeout == check_review_arrival.HTTP_TIMEOUT_SECONDS
        outcome = next(outcomes)
        if isinstance(outcome, URLError):
            raise outcome
        return io.BytesIO(json.dumps(outcome).encode())

    def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(check_review_arrival, "urlopen", fake_urlopen)
    monkeypatch.setattr(check_review_arrival.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(check_review_arrival.time, "sleep", no_sleep)

    assert check_review_arrival.main() == 0
