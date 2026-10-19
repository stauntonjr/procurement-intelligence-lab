import json
from email.message import Message
from pathlib import Path
from typing import Self
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from pytest import MonkeyPatch

from tools import run_roadmap_review as review

VALID_REPORT = """## Current state
Current evidence.
## Drift or conflicts
No confirmed drift.
## Missing durable intake
None found.
## Recommended human decisions
No decision required.
"""


def test_parse_report_requires_the_complete_advisory_contract() -> None:
    assert review.parse_report(json.dumps({"response": VALID_REPORT})) == VALID_REPORT


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("", "valid JSON"),
        ("not-json", "valid JSON"),
        ("[]", "JSON object"),
        ('{"response":""}', "non-empty response"),
        ('{"response":"## Current state\\nincomplete"}', "exactly the required headings"),
        (
            json.dumps({"response": "".join(f"## {h}\n" for h in review.REQUIRED_HEADINGS)}),
            "non-empty section",
        ),
    ],
)
def test_parse_report_rejects_missing_or_malformed_reviews(stdout: str, message: str) -> None:
    with pytest.raises(review.RoadmapReviewError, match=message):
        review.parse_report(stdout)


def test_snapshot_retains_sources_and_rejects_missing_or_oversized_inputs(tmp_path: Path) -> None:
    (tmp_path / "one.md").write_text("source evidence")
    payload = review.build_snapshot(tmp_path, ("one.md",))
    assert json.loads(payload) == {"one.md": "source evidence"}
    with pytest.raises(review.RoadmapReviewError, match="missing"):
        review.build_snapshot(tmp_path, ("absent.md",))
    with pytest.raises(review.RoadmapReviewError, match="size limit"):
        review.build_snapshot(tmp_path, ("one.md",), max_bytes=3)


def test_one_request_has_all_context_and_no_tools(monkeypatch: MonkeyPatch) -> None:
    requests: list[Request] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            return json.dumps(
                {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "parts": [{"text": json.dumps({"response": VALID_REPORT})}]
                            },
                        }
                    ]
                }
            ).encode()

    def open_request(request: Request, *, timeout: int) -> Response:
        requests.append(request)
        assert timeout == 180
        return Response()

    monkeypatch.setattr(review.urllib.request, "urlopen", open_request)
    assert review.generate_report("instructions", "snapshot", "test-secret") == VALID_REPORT
    assert len(requests) == 1
    request = requests[0]
    assert request.full_url.endswith("/gemini-3.8-flash:generateContent")
    assert isinstance(request.data, bytes)
    body = json.loads(request.data)
    assert body["systemInstruction"]["parts"][0]["text"] == "instructions"
    assert body["contents"][0]["parts"][0]["text"] == "snapshot"
    assert "tools" not in body
    assert "test-secret" not in request.full_url


def test_quota_failure_is_actionable_and_never_retried(monkeypatch: MonkeyPatch) -> None:
    calls: list[bool] = []

    def unavailable(*args: object, **kwargs: object) -> None:
        calls.append(True)
        raise HTTPError("https://example.invalid", 429, "private provider body", Message(), None)

    monkeypatch.setattr(review.urllib.request, "urlopen", unavailable)
    with pytest.raises(review.RoadmapReviewError, match="429.*quota") as caught:
        review.generate_report("instructions", "snapshot", "test-secret")
    assert len(calls) == 1
    assert "private provider body" not in str(caught.value)
    assert "test-secret" not in str(caught.value)


@pytest.mark.parametrize(
    "candidate",
    [
        {},
        {"candidates": []},
        {
            "candidates": [
                {
                    "finishReason": "MAX_TOKENS",
                    "content": {"parts": [{"text": json.dumps({"response": VALID_REPORT})}]},
                }
            ]
        },
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [{"thought": True, "text": json.dumps({"response": VALID_REPORT})}]
                    },
                }
            ]
        },
    ],
)
def test_incomplete_provider_response_is_not_a_report(candidate: object) -> None:
    with pytest.raises(review.RoadmapReviewError):
        review.parse_provider_response(candidate)


def test_workflow_uses_one_pinned_model_request_without_agent_tools() -> None:
    workflow = Path(".github/workflows/roadmap-stewardship.yml").read_text()
    assert "python -m tools.run_roadmap_review" in workflow
    assert "npm ci" not in workflow
    assert "continue-on-error" not in workflow
    assert "persist-credentials: false" in workflow
    assert "timeout-minutes: 5" in workflow
    assert "GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}" in workflow
    assert "contents: write" not in workflow
    assert "issues: write" not in workflow
