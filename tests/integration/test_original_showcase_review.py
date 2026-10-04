"""Actual local source-selected HTTP/CLI review, with a bounded model double."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from threading import Thread

import pytest

from procurement_intelligence_lab.interfaces.review_web import create_server
from procurement_intelligence_lab.platform.semantics.interpretation import ModelReply
from tests.contract.test_original_showcase_sources import CASES
from tests.integration.test_review_web import TOKEN, request, review

CUTOFF = "2026-01-15T00:00:00Z"


class Model:
    calls = 0

    def interpret(
        self, question: str, items: tuple[str, ...], project: str, as_of: str
    ) -> ModelReply:
        self.calls += 1
        assert (
            question == "Compare GPU-A" and items == ("GPU-A",) and project == "synthetic-project"
        )
        assert not any(
            word in question for word in ("showcase", "mismatch", "unresolved", "missing")
        )
        return ModelReply(
            json.dumps(
                {
                    "status": "investigate",
                    "item": "GPU-A",
                    "project": project,
                    "as_of": as_of,
                    "reason": "none",
                }
            ),
            120,
            40,
        )


@pytest.mark.parametrize("selection,scenario,required,observed,status,reason", CASES)
def test_original_http_sources_model_and_review(
    tmp_path: Path,
    selection: str,
    scenario: object,
    required: str | None,
    observed: str | None,
    status: str,
    reason: str | None,
) -> None:
    server = create_server(
        tmp_path / "review.db",
        project="synthetic-project",
        token=TOKEN,
        port=0,
        model_endpoint="http://127.0.0.1:8000/v1",
        sources=selection,
    )
    assert server.questions is not None
    model = Model()
    server.questions = replace(server.questions, model=model)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = ("127.0.0.1", server.server_port)
    try:
        assert (
            request(
                address,
                "/api/ask",
                {"question": "Compare GPU-A", "as_of": CUTOFF, "sources": "showcase-a-only"},
            )[0]
            == 422
        )
        assert model.calls == 0
        code, result, _ = request(
            address, "/api/ask", {"question": "Compare GPU-A", "as_of": CUTOFF}
        )
        assert code == 200 and model.calls == 1
        view = result["workflow"]
        assert view["saved"] is None
        facts = json.loads(view["brief"]["content_json"])
        assert (
            facts["required_quantity"],
            facts["ordered_quantity"],
            facts["status"],
            facts["reason"],
        ) == (required, observed, status, reason)
        for ref in facts["evidence"]:
            code, source, _ = request(
                address,
                "/api/source?run_id=" + view["run_id"] + "&evidence_id=" + ref["evidence_id"],
            )
            assert code == 200 and source["evidence"] == ref and source["cells"][0] == "GPU-A"
        assert request(address, "/api/recover", {"run_id": view["run_id"]})[1] == result
        done = request(address, "/api/review", review(view))[1]
        assert (
            done["status"] == "completed"
            and request(address, "/api/review", review(view))[1] == done
        )
        assert model.calls == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_wrong_source_project_is_rejected_before_persistence(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_server(
            tmp_path / "wrong.db", project="atlas", token=TOKEN, port=0, sources="showcase-a-order"
        )
    assert not (tmp_path / "wrong.db").exists()
    with pytest.raises(ValueError):
        create_server(tmp_path / "wrong.db", project="synthetic-project", token=TOKEN, port=0)


def invoke(
    path: Path, selection: str, operation: str, *arguments: str
) -> tuple[int, dict[str, object]]:
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.workflow",
            "--database",
            str(path),
            "--project",
            "synthetic-project",
            "--sources",
            selection,
            operation,
            *arguments,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return run.returncode, json.loads(run.stdout)


def test_public_cli_restart_and_cross_source_version_refusal(tmp_path: Path) -> None:
    database = tmp_path / "review.db"
    code, view = invoke(database, "showcase-a-order", "start", "--item", "GPU-A", "--as-of", CUTOFF)
    assert code == 0
    run = str(view["run_id"])
    assert invoke(database, "showcase-a-order", "recover", "--run-id", run)[1] == view
    import sqlite3

    with sqlite3.connect(database) as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM agent_events").fetchone()[0]
    assert invoke(database, "showcase-a-b-order", "recover", "--run-id", run)[0] == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM agent_events").fetchone()[0] == event_count
    assert invoke(database, "showcase-a-order", "recover", "--run-id", run)[1] == view
    assert (
        invoke(
            database,
            "showcase-a-order",
            "start",
            "--item",
            "GPU-A",
            "--as-of",
            "2026-10-01T00:00:00Z",
        )[0]
        == 1
    )


def test_original_page_explains_observation_and_fixed_sources(tmp_path: Path) -> None:
    server = create_server(
        tmp_path / "page.db",
        project="synthetic-project",
        token=TOKEN,
        port=0,
        sources="showcase-a-b-order",
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    import urllib.request

    try:
        with urllib.request.urlopen(server.origin) as response:
            page = response.read().decode()
        assert "Order observation: " in page and "Assessed ordered: " not in page
        assert "2026-01-15T00:00:00Z" in page and "GPU-C" not in page
        assert "not_assessed" in page and "showcase-a-b-order" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
