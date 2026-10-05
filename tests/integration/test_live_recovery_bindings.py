"""Foreign durable payloads cannot authorize work during real HTTP recovery."""

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from threading import Thread

import pytest

from procurement_intelligence_lab.adapters.langgraph_review import LangGraphReviewRuntime
from procurement_intelligence_lab.interfaces.review_web import create_server
from procurement_intelligence_lab.platform.semantics.interpretation import InterpretationCall
from tests.contract.test_exact_brief_review import ARGS
from tests.integration.test_review_web import TOKEN, request


@pytest.mark.parametrize("corruption", ["checkpoint", "journal"])
def test_foreign_run_binding_rejected_before_any_tool_work(tmp_path: Path, corruption: str) -> None:
    path = tmp_path / "runs.db"
    web = create_server(
        path, project="atlas", token=TOKEN, port=0, model_endpoint="http://127.0.0.1:1/v1"
    )
    assert web.questions is not None
    runs = web.composition.runs
    a = runs.start(context=web.context)
    b = runs.start(context=web.context)
    for run in (a, b):
        call = InterpretationCall(run.run_id, "0" * 64, ARGS.request.as_of)
        web.questions.store.create(call)
        if run == a:
            web.questions.store.finish(
                replace(call, status="investigate", item="GPU-A", elapsed_seconds=1)
            )
    runtime = web.composition.runtime
    assert isinstance(runtime, LangGraphReviewRuntime)
    if corruption == "checkpoint":
        config = runtime._config(a.run_id, web.context)  # pyright: ignore[reportPrivateUsage]
        with runtime._graph() as graph:  # pyright: ignore[reportPrivateUsage]
            graph.update_state(
                config,
                {
                    "run_id": b.run_id,
                    "item": "GPU-A",
                    "as_of": ARGS.request.as_of.isoformat(),
                    "brief_id": "",
                    "digest": "",
                    "snapshot_id": "",
                    "decision": "",
                    "done": False,
                },
                as_node="__start__",
            )
            assert graph.get_state(config).next == ("draft",)
    else:
        with sqlite3.connect(path) as db:
            raw = json.loads(
                db.execute(
                    "SELECT payload FROM interpretation_calls WHERE run_id=?", (a.run_id,)
                ).fetchone()[0]
            )
            raw["run_id"] = b.run_id
            db.execute(
                "UPDATE interpretation_calls SET payload=? WHERE run_id=?",
                (json.dumps(raw), a.run_id),
            )
    thread = Thread(target=web.serve_forever, daemon=True)
    thread.start()
    try:
        code, _, _ = request(("127.0.0.1", web.server_port), "/api/recover", {"run_id": a.run_id})
        assert code == 503
        assert len(runs.events(a.run_id, context=web.context)) == 1
        assert len(runs.events(b.run_id, context=web.context)) == 1
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT COUNT(*) FROM review_briefs").fetchone()[0] == 0
        assert web.questions.store.get(b.run_id).status == "pending"
    finally:
        web.shutdown()
        web.server_close()
        thread.join()
