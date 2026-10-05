"""Exercise the shipped HTTP handler and every cited original source."""

import json
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest

from procurement_intelligence_lab.interfaces.web import InspectorHandler


@pytest.fixture
def corpus_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), InspectorHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def fetch(url: str) -> tuple[int, dict[str, object]]:
    try:
        with urlopen(url, timeout=10) as response:
            return response.status, cast(dict[str, object], json.load(response))
    except HTTPError as error:
        return error.code, cast(dict[str, object], json.load(error))


def test_http_gold_and_original_sources(corpus_server: str) -> None:
    gold = json.loads(
        (Path(__file__).resolve().parents[2] / "evals/procurement_corpus/v1/gold.json").read_text()
    )
    for case in gold["cases"]:
        status, data = fetch(
            corpus_server
            + "/api/corpus/investigate?"
            + urlencode({"project": "atlas", "item": case["item"], "as_of": case["as_of"]})
        )
        assert status == 200
        assert (data["status"], data["reason"], data["required_quantity"]) == (
            case["status"],
            case["reason"],
            case["required_quantity"],
        )
        if case["id"] == "mismatch":
            assert data["ordered_quantity"] == "6"
        if case["id"] == "fractional":
            assert data["ordered_quantity"] == "1.50"
        if case["id"] == "zero":
            assert data["ordered_quantity"] == "0"
        if case["id"] == "before-boundary":
            assert set(cast(dict[str, str], data["input_dispositions"]).values()) == {
                "rejected_future"
            }
        assert data["governance_policy_id"] == "procurement-governing-claims/v1"
        assert data["governance_decision_id"]
        evidence = cast(list[dict[str, object]], data["evidence"])
        # Every returned source link is a real HTTP request, including authority sidecars.
        for ref in evidence:
            code, source = fetch(corpus_server + str(ref["url"]))
            assert code == 200
            assert cast(dict[str, object], source["evidence"])["evidence_id"] == ref["evidence_id"]
            if ref["location_kind"] == "tabular":
                assert cast(list[str], source["cells"])[0] == case["item"]
            else:
                assert cast(dict[str, object], source["authority"])["document"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("project=foreign&item=GPU-A&as_of=2026-10-01T00:00:00Z", 403),
        ("project=atlas&item=unknown&as_of=2026-10-01T00:00:00Z", 404),
        ("project=atlas&item=GPU-A&as_of=2026-10-01", 422),
        ("project=atlas&item=GPU-A&as_of=no", 422),
        ("project=atlas&item=GPU-A&item=GPU-B&as_of=2026-10-01T00:00:00Z", 422),
        ("project=atlas&item=&as_of=2026-10-01T00:00:00Z", 422),
        ("project=atlas&item=GPU-A&as_of=2026-10-01T00:00:00Z&tenant=elsewhere", 422),
    ],
)
def test_http_typed_failures(corpus_server: str, query: str, expected: int) -> None:
    status, data = fetch(corpus_server + "/api/corpus/investigate?" + query)
    assert status == expected
    assert data["code"] and data["category"]


def test_source_unknown_and_page(corpus_server: str) -> None:
    assert fetch(corpus_server + "/api/corpus/source?project=atlas&evidence_id=missing")[0] == 404
    with urlopen(corpus_server + "/corpus") as response:
        page = response.read().decode()
        assert 'name="item"' in page and "960 source-row occurrences" in page


def test_invalid_source_has_typed_503(
    corpus_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.interfaces import corpus_http

    (tmp_path / "manifest.json").write_text('{"schema_version":"unsupported"}')
    monkeypatch.setattr(
        corpus_http, "SyntheticCorpusReader", lambda: SyntheticCorpusReader(tmp_path)
    )
    status, data = fetch(
        corpus_server
        + "/api/corpus/investigate?project=atlas&item=GPU-A&as_of=2026-10-01T00:00:00Z"
    )
    assert status == 503
    assert data["code"] == "corpus_admission_failed" and data["category"] == "infrastructure"


def test_source_request_admits_once_and_revalidates_next_request(
    corpus_server: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import patch

    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.interfaces import corpus_http

    reader = SyntheticCorpusReader()
    _, result = fetch(
        corpus_server
        + "/api/corpus/investigate?project=atlas&item=GPU-A&as_of=2026-10-01T00:00:00Z"
    )
    ref = cast(list[dict[str, object]], result["evidence"])[0]
    monkeypatch.setattr(corpus_http, "SyntheticCorpusReader", lambda: reader)
    with patch.object(
        SyntheticCorpusReader,
        "_load",
        autospec=True,
        side_effect=vars(SyntheticCorpusReader)["_load"],
    ) as load:
        assert fetch(corpus_server + str(ref["url"]))[0] == 200
        assert load.call_count == 1
        assert fetch(corpus_server + str(ref["url"]))[0] == 200
        assert load.call_count == 2


def test_projects_with_same_item_remain_isolated(corpus_server: str) -> None:
    requests = {
        project: fetch(
            corpus_server
            + "/api/corpus/investigate?"
            + urlencode({"project": project, "item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"})
        )
        for project in ("atlas", "borealis", "cinder", "delta")
    }
    assert all(status == 200 for status, _ in requests.values())
    assert {project: data["required_quantity"] for project, (_, data) in requests.items()} == {
        "atlas": "8",
        "borealis": "6",
        "cinder": "6",
        "delta": "12",
    }
    reference = cast(list[dict[str, object]], requests["atlas"][1]["evidence"])[0]
    status, _ = fetch(
        corpus_server
        + "/api/corpus/source?"
        + urlencode({"project": "borealis", "evidence_id": reference["evidence_id"]})
    )
    assert status == 404
