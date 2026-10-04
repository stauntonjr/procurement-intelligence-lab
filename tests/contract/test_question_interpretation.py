"""One model interpretation, strict authority boundary and durable recovery."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.sqlite_interpretation import SqliteInterpretationStore
from procurement_intelligence_lab.application.question_review import QuestionReviewService
from procurement_intelligence_lab.interfaces.live_review import compose_live
from procurement_intelligence_lab.platform.semantics.interpretation import ModelReply
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    ScopeAuthorizationError,
)
from tests.contract.test_exact_brief_review import ARGS, HUMAN


class Model:
    calls = 0
    text = json.dumps(
        {
            "status": "investigate",
            "item": "GPU-A",
            "project": "atlas",
            "as_of": ARGS.request.as_of.isoformat(),
            "reason": "none",
        }
    )

    def interpret(
        self, question: str, items: tuple[str, ...], project: str, as_of: str
    ) -> ModelReply:
        self.calls += 1
        assert question and "GPU-A" in items and project == "atlas" and as_of
        return ModelReply(self.text, 120, 40)


def service(path: Path, model: Model) -> QuestionReviewService:
    composition = compose_live(path)
    return QuestionReviewService(composition, model, SqliteInterpretationStore(path))


def test_same_run_durable_result_recovery_and_no_model_save_authority(tmp_path: Path) -> None:
    model = Model()
    path = tmp_path / "runs.db"
    live = service(path, model)
    outcome = live.ask("Compare GPU-A orders to requirements", ARGS.request.as_of, context=HUMAN)
    assert outcome.call.status == "investigate" and outcome.view is not None
    assert outcome.call.run_id == outcome.view.run_id
    assert model.calls == 1
    assert '"required_quantity":"8"' in outcome.view.brief.content_json
    assert '"ordered_quantity":"6"' in outcome.view.brief.content_json
    assert outcome.view.saved is None
    again = service(path, model).recover(outcome.call.run_id, context=HUMAN)
    assert again == outcome and model.calls == 1
    operational = replace(
        HUMAN, permissions=frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE})
    )
    with pytest.raises(ScopeAuthorizationError):
        live.composition.runtime.review(
            outcome.view.run_id,
            outcome.view.brief.brief_id,
            outcome.view.brief.digest,
            "approve",
            context=operational,
        )


@pytest.mark.parametrize(
    "text,status",
    [
        ('{"status":"investigate"}', "failed"),
        (
            json.dumps(
                {
                    "status": "investigate",
                    "item": "GPU-A",
                    "project": "delta",
                    "as_of": ARGS.request.as_of.isoformat(),
                    "reason": "none",
                }
            ),
            "failed",
        ),
        (
            json.dumps(
                {
                    "status": "investigate",
                    "item": "UNKNOWN",
                    "project": "atlas",
                    "as_of": ARGS.request.as_of.isoformat(),
                    "reason": "none",
                }
            ),
            "failed",
        ),
        (
            json.dumps(
                {
                    "status": "investigate",
                    "item": "GPU-A",
                    "project": "atlas",
                    "as_of": "2026-11-01T00:00:00Z",
                    "reason": "none",
                }
            ),
            "failed",
        ),
        (
            json.dumps(
                {
                    "status": "clarify",
                    "item": None,
                    "project": "atlas",
                    "as_of": None,
                    "reason": "item_ambiguous",
                }
            ),
            "clarify",
        ),
        (
            json.dumps(
                {
                    "status": "unsupported",
                    "item": None,
                    "project": "atlas",
                    "as_of": None,
                    "reason": "unsupported",
                }
            ),
            "unsupported",
        ),
    ],
)
def test_closed_proposals_do_not_invoke_tools(tmp_path: Path, text: str, status: str) -> None:
    model = Model()
    model.text = text
    live = service(tmp_path / "runs.db", model)
    result = live.ask("a synthetic question", ARGS.request.as_of, context=HUMAN)
    assert result.call.status == status and result.view is None
    assert len(live.composition.runs.events(result.call.run_id, context=HUMAN)) == 1
    assert result.call.prompt_tokens == 120 and result.call.completion_tokens == 40
    assert live.recover(result.call.run_id, context=HUMAN) == result and model.calls == 1


@pytest.mark.parametrize("question", ["", " ", "x" * 1001])
def test_bad_request_never_calls_model(tmp_path: Path, question: str) -> None:
    model = Model()
    with pytest.raises(ValueError):
        service(tmp_path / "runs.db", model).ask(question, ARGS.request.as_of, context=HUMAN)
    assert model.calls == 0


def test_status_does_not_resume_or_reinterpret_pending_attempt(tmp_path: Path) -> None:
    from hashlib import sha256

    from procurement_intelligence_lab.platform.semantics.interpretation import InterpretationCall

    model = Model()
    live = service(tmp_path / "runs.db", model)
    run = live.composition.runs.start(context=HUMAN)
    live.store.create(
        InterpretationCall(run.run_id, sha256(b"interrupted").hexdigest(), ARGS.request.as_of)
    )
    assert live.status(run.run_id, context=HUMAN).call.status == "pending"
    assert live.recover(run.run_id, context=HUMAN).view is None and model.calls == 0


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        "null",
        "{}",
        '{"status":"investigate","status":"clarify"}',
        '{"status":"investigate","item":"GPU-A","project":"atlas","as_of":"2026-10-01T00:00:00Z","reason":"none","permissions":["act"]}',
    ],
)
def test_malformed_or_authority_proposals_are_durable_failures(tmp_path: Path, raw: str) -> None:
    model = Model()
    model.text = raw
    live = service(tmp_path / "runs.db", model)
    result = live.ask("Compare GPU-A", ARGS.request.as_of, context=HUMAN)
    assert result.call.reason == "invalid_model_output" and result.view is None


def test_accepted_intent_survives_crash_before_workflow_creation(tmp_path: Path) -> None:
    from hashlib import sha256

    from procurement_intelligence_lab.platform.semantics.interpretation import InterpretationCall

    model = Model()
    live = service(tmp_path / "runs.db", model)
    run = live.composition.runs.start(context=HUMAN)
    pending = InterpretationCall(
        run.run_id, sha256(b"Compare GPU-A").hexdigest(), ARGS.request.as_of
    )
    live.store.create(pending)
    live.store.finish(
        replace(
            pending,
            status="investigate",
            item="GPU-A",
            elapsed_seconds=1,
            prompt_tokens=10,
            completion_tokens=3,
        )
    )
    result = live.recover(run.run_id, context=HUMAN)
    assert result.view is not None and result.view.status == "awaiting_review" and model.calls == 0


def test_foreign_scope_and_changed_version_cannot_read_journal(tmp_path: Path) -> None:
    from procurement_intelligence_lab.platform.semantics.agent_runs import RunConflict, RunNotFound

    model = Model()
    live = service(tmp_path / "runs.db", model)
    result = live.ask("Compare GPU-A", ARGS.request.as_of, context=HUMAN)
    with pytest.raises(RunNotFound):
        live.status(result.call.run_id, context=replace(HUMAN, project_id="delta"))
    live.composition.runs.versions = replace(live.composition.runs.versions, model="changed")
    with pytest.raises(RunConflict):
        live.recover(result.call.run_id, context=HUMAN)
    assert model.calls == 1


def test_tool_failure_keeps_accepted_intent_and_actual_failure_event(tmp_path: Path) -> None:
    from unittest.mock import Mock

    from procurement_intelligence_lab.application.corpus_agent_tools import ToolExecutionError
    from procurement_intelligence_lab.platform.semantics.interpretation import ModelFailure

    model = Model()
    live = service(tmp_path / "runs.db", model)
    # The runtime uses the same mutable application brief service in this composition.
    from procurement_intelligence_lab.adapters.langgraph_review import LangGraphReviewRuntime

    assert isinstance(live.composition.runtime, LangGraphReviewRuntime)
    core = live.composition.runtime.service
    failed = Mock()
    failed.investigate.side_effect = TimeoutError("injected")
    core.tools = replace(core.tools, investigator=failed)
    with pytest.raises(ToolExecutionError):
        live.ask("Compare GPU-A", ARGS.request.as_of, context=HUMAN)
    run = live.composition.runs.recent(context=HUMAN)[0]
    assert live.store.get(run.run_id).status == "investigate"
    events = live.composition.runs.events(run.run_id, context=HUMAN)
    assert events[-1].kind.value == "tool_failed" and events[-1].error_code == "tool_timeout"
    assert model.calls == 1
    with pytest.raises(ModelFailure):
        live.store.finish(live.store.get(run.run_id))


def test_application_rejects_foreign_call_from_any_store_port(tmp_path: Path) -> None:
    from unittest.mock import Mock

    from procurement_intelligence_lab.platform.semantics.interpretation import ModelFailure

    model = Model()
    live = service(tmp_path / "runs.db", model)
    result = live.ask("Compare GPU-A", ARGS.request.as_of, context=HUMAN)
    bad = Mock(wraps=live.store)
    bad.get.return_value = replace(result.call, run_id="foreign-run")
    poisoned = replace(live, store=bad)
    for operation in (poisoned.status, poisoned.recover):
        with pytest.raises(ModelFailure):
            operation(result.call.run_id, context=HUMAN)
    assert model.calls == 1


@pytest.mark.parametrize(
    "question,item", [("Compare GPU-A", "GPU-B"), ("Compare GPU-A and GPU-B", "GPU-A")]
)
def test_model_cannot_select_an_admitted_item_without_unique_literal_support(
    tmp_path: Path, question: str, item: str
) -> None:
    model = Model()
    raw = json.loads(model.text)
    raw["item"] = item
    model.text = json.dumps(raw)
    live = service(tmp_path / "runs.db", model)
    result = live.ask(question, ARGS.request.as_of, context=HUMAN)
    assert result.call.status == "failed" and result.call.reason == "invalid_model_output"
    assert (
        result.view is None
        and len(live.composition.runs.events(result.call.run_id, context=HUMAN)) == 1
    )
