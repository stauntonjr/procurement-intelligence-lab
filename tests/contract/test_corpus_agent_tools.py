"""Actual service invocation and scope-owned audit, not model-reported calls."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from procurement_intelligence_lab.adapters.sqlite_agent_runs import SqliteRunStore
from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.corpus_agent_tools import (
    TOOL_SCHEMA_VERSION,
    CorpusAgentTools,
    InvestigateToolArgs,
    SourceToolArgs,
    ToolExecutionError,
)
from procurement_intelligence_lab.application.corpus_investigation import (
    CorpusInvestigationService,
    InvestigationRequest,
)
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEventKind,
    ExecutionKind,
    RunNotFound,
    RunVersions,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)

CONTEXT = RequestContext(
    "demo",
    "synthetic-tenant",
    "atlas",
    "lab",
    frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE}),
    "test",
)


def setup(path: Path) -> tuple[CorpusAgentTools, AgentRunService, str]:
    runs = AgentRunService(
        SqliteRunStore(path),
        versions=RunVersions("fixture", "none", "p1", TOOL_SCHEMA_VERSION, "f1", "a1"),
        execution_kind=ExecutionKind.FIXTURE,
    )
    run = runs.start(context=CONTEXT)
    reader = SyntheticCorpusReader()
    return CorpusAgentTools(CorpusInvestigationService(reader), reader, runs), runs, run.run_id


def test_tools_equal_direct_service_and_original_source(tmp_path: Path) -> None:
    tools, runs, run_id = setup(tmp_path / "runs.db")
    for item in ("GPU-A", "GPU-C", "GPU-D"):
        args = InvestigateToolArgs.from_mapping(
            {"item": item, "as_of": "2026-10-01T00:00:00+00:00"}
        )
        result = tools.investigate(run_id, args, context=CONTEXT)
        direct = CorpusInvestigationService(SyntheticCorpusReader()).investigate(
            InvestigationRequest(item, datetime(2026, 10, 1, tzinfo=UTC)), context=CONTEXT
        )
        from procurement_intelligence_lab.interfaces.corpus_dto import investigation_dto

        assert investigation_dto(result, CONTEXT) == investigation_dto(direct, CONTEXT)
        ref = result.evidence[0]
        source = tools.source(run_id, SourceToolArgs(ref.evidence_id), context=CONTEXT)
        assert source == SyntheticCorpusReader().source(ref, context=CONTEXT)
    events = runs.events(run_id, context=CONTEXT)
    assert sum(e.kind == AgentEventKind.TOOL_STARTED for e in events) == 6
    assert sum(e.kind == AgentEventKind.TOOL_SUCCEEDED for e in events) == 6


@pytest.mark.parametrize(
    "arguments",
    [
        {"item": "GPU-A", "as_of": "2026-10-01", "project": "delta"},
        {"item": "GPU-A", "as_of": "2026-10-01"},
        {"item": 12, "as_of": "2026-10-01T00:00:00Z"},
        {"item": "", "as_of": "2026-10-01T00:00:00Z"},
    ],
)
def test_model_arguments_cannot_grant_authority(arguments: dict[str, object]) -> None:
    with pytest.raises((ValueError, TypeError)):
        InvestigateToolArgs.from_mapping(arguments)
    with pytest.raises((ValueError, TypeError)):
        SourceToolArgs.from_mapping({"evidence_id": "ref", "permissions": ["review"]})


def test_scope_and_permissions_precede_actual_lookup(tmp_path: Path) -> None:
    tools, runs, run_id = setup(tmp_path / "runs.db")
    lookup = Mock()
    constrained = CorpusAgentTools(tools.investigator, lookup, runs)
    with pytest.raises(ScopeAuthorizationError):
        constrained.source(
            run_id,
            SourceToolArgs("ref"),
            context=replace(CONTEXT, permissions=frozenset({Permission.READ_STATE})),
        )
    with pytest.raises(RunNotFound):
        constrained.source(
            run_id, SourceToolArgs("ref"), context=replace(CONTEXT, project_id="delta")
        )
    lookup.source_by_id.assert_not_called()
    assert len(runs.events(run_id, context=CONTEXT)) == 1


def test_tool_timeout_is_recorded_without_success(tmp_path: Path) -> None:
    tools, runs, run_id = setup(tmp_path / "runs.db")
    lookup = Mock()
    lookup.source_by_id.side_effect = TimeoutError("synthetic timeout")
    constrained = CorpusAgentTools(tools.investigator, lookup, runs)
    with pytest.raises(ToolExecutionError):
        constrained.source(run_id, SourceToolArgs("ref"), context=CONTEXT)
    events = runs.events(run_id, context=CONTEXT)
    assert events[-1].kind == AgentEventKind.TOOL_FAILED and events[-1].error_code == "tool_timeout"
    assert not any(e.kind == AgentEventKind.TOOL_SUCCEEDED for e in events)


def test_foreign_source_id_cannot_grant_scope(tmp_path: Path) -> None:
    tools, runs, run_id = setup(tmp_path / "runs.db")
    other = SyntheticCorpusReader().inventory(context=replace(CONTEXT, project_id="delta"))
    with pytest.raises(ToolExecutionError):
        tools.source(run_id, SourceToolArgs(other.facts[0].evidence.evidence_id), context=CONTEXT)
    assert runs.events(run_id, context=CONTEXT)[-1].kind == AgentEventKind.TOOL_FAILED


def test_failed_success_audit_does_not_return_completed_tool(tmp_path: Path) -> None:
    from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError
    from procurement_intelligence_lab.application.agent_trajectory import evaluate_trajectory

    tools, runs, run_id = setup(tmp_path / "runs.db")
    real = runs.store
    store = Mock(wraps=real)

    def append(event: object, *, context: RequestContext) -> None:
        from typing import cast

        from procurement_intelligence_lab.platform.semantics.agent_runs import AgentEvent

        typed = cast(AgentEvent, event)
        if typed.kind == AgentEventKind.TOOL_SUCCEEDED:
            raise RunStoreError("injected audit failure")
        real.append(typed, context=context)

    store.append.side_effect = append
    runs.store = store
    ref = SyntheticCorpusReader().inventory(context=CONTEXT).facts[0].evidence
    with pytest.raises(RunStoreError):
        tools.source(run_id, SourceToolArgs(ref.evidence_id), context=CONTEXT)
    events = runs.events(run_id, context=CONTEXT)
    assert events[-1].kind == AgentEventKind.TOOL_STARTED
    assert (
        evaluate_trajectory(
            runs.resume(run_id, context=CONTEXT), events, required_tools=("inspect_source",)
        ).outcome
        == "unknown"
    )


@pytest.mark.parametrize(
    "failure", [OSError("injected unavailable"), ValueError("injected invalid result")]
)
def test_closed_error_classification(tmp_path: Path, failure: Exception) -> None:
    tools, runs, run_id = setup(tmp_path / "runs.db")
    lookup = Mock()
    lookup.source_by_id.side_effect = failure
    with pytest.raises(ToolExecutionError):
        CorpusAgentTools(tools.investigator, lookup, runs).source(
            run_id, SourceToolArgs("ref"), context=CONTEXT
        )
    event = runs.events(run_id, context=CONTEXT)[-1]
    assert event.error_code == (
        "tool_unavailable" if isinstance(failure, OSError) else "invalid_tool_result"
    )


@pytest.mark.parametrize("operation", ["investigate", "source"])
@pytest.mark.parametrize("mutation", ["corrupt", "missing"])
def test_actual_admission_failure_keeps_infrastructure_boundary(
    tmp_path: Path, operation: str, mutation: str
) -> None:
    import shutil

    from procurement_intelligence_lab.adapters.synthetic_corpus import DEFAULT_ROOT
    from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError

    _tools, runs, run_id = setup(tmp_path / "runs.db")
    root = tmp_path / "corpus"
    shutil.copytree(DEFAULT_ROOT, root)
    reader = SyntheticCorpusReader(root=root)
    ref = reader.inventory(context=CONTEXT).facts[0].evidence
    path = root / (ref.artifact_id + ".xlsx")
    if mutation == "corrupt":
        path.write_bytes(b"synthetic corrupt workbook")
    else:
        path.unlink()
    actual = CorpusAgentTools(CorpusInvestigationService(reader), reader, runs)
    with pytest.raises(ToolExecutionError) as caught:
        if operation == "source":
            actual.source(run_id, SourceToolArgs(ref.evidence_id), context=CONTEXT)
        else:
            actual.investigate(
                run_id,
                InvestigateToolArgs.from_mapping(
                    {"item": "GPU-A", "as_of": "2026-10-01T00:00:00+00:00"}
                ),
                context=CONTEXT,
            )
    assert isinstance(caught.value.__cause__, CorpusAdmissionError)
    assert caught.value.as_dict() == {
        "code": "pil.infrastructure.agent_tool_admission_failed",
        "category": "infrastructure",
    }
    events = runs.events(run_id, context=CONTEXT)
    assert events[-1].error_code == "corpus_admission_failed"
    assert not any(e.kind == AgentEventKind.TOOL_SUCCEEDED for e in events)


def test_invalid_port_output_records_failure_not_success(tmp_path: Path) -> None:
    from procurement_intelligence_lab.ports.corpus import CorpusSourceRecord

    tools, runs, run_id = setup(tmp_path / "r.db")
    args = InvestigateToolArgs.from_mapping({"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"})
    actual = tools.investigator.investigate(args.request, context=CONTEXT)
    lookup = Mock()
    lookup.source_by_id.return_value = CorpusSourceRecord(
        actual.evidence[0], "private malformed JSON"
    )
    with pytest.raises(ToolExecutionError, match="agent_tool_invalid_result"):
        replace(tools, lookup=lookup).source(
            run_id, SourceToolArgs(actual.evidence[0].evidence_id), context=CONTEXT
        )
    investigator = Mock()
    investigator.investigate.return_value = replace(actual, snapshot_id="")
    with pytest.raises(ToolExecutionError, match="agent_tool_invalid_result"):
        replace(tools, investigator=investigator).investigate(run_id, args, context=CONTEXT)
    events = runs.events(run_id, context=CONTEXT)
    assert sum(e.kind == AgentEventKind.TOOL_FAILED for e in events) == 2
    assert not any(e.kind == AgentEventKind.TOOL_SUCCEEDED for e in events)


@pytest.mark.parametrize("field", ["evidence", "governed"])
def test_malformed_nested_investigation_never_records_success(tmp_path: Path, field: str) -> None:
    from typing import Any, cast

    tools, runs, run_id = setup(tmp_path / "r.db")
    args = InvestigateToolArgs.from_mapping({"item": "GPU-A", "as_of": "2026-10-01T00:00:00Z"})
    actual = tools.investigator.investigate(args.request, context=CONTEXT)
    invalid = (
        replace(actual, evidence=cast(Any, (None,)))
        if field == "evidence"
        else replace(actual, governed=cast(Any, None))
    )
    investigator = Mock()
    investigator.investigate.return_value = invalid
    with pytest.raises(ToolExecutionError, match="agent_tool_invalid_result"):
        replace(tools, investigator=investigator).investigate(run_id, args, context=CONTEXT)
    events = runs.events(run_id, context=CONTEXT)
    assert events[-1].kind == AgentEventKind.TOOL_FAILED
    assert not any(e.kind == AgentEventKind.TOOL_SUCCEEDED for e in events)
