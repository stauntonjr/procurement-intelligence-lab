"""Local run-ledger probe with fixed synthetic caller; no live agent execution."""

import argparse
import json
from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

from procurement_intelligence_lab.adapters.runtime_identity import application_revision
from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError, SqliteRunStore
from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.agent_trajectory import (
    evaluate_trajectory,
    summarize_trajectories,
)
from procurement_intelligence_lab.application.corpus_agent_tools import (
    TOOL_SCHEMA_VERSION,
    CorpusAgentTools,
    InvestigateToolArgs,
    SourceToolArgs,
    ToolExecutionError,
)
from procurement_intelligence_lab.application.corpus_investigation import CorpusInvestigationService
from procurement_intelligence_lab.interfaces.corpus_dto import investigation_dto, source_dto
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    AgentEventKind,
    ExecutionKind,
    RunConflict,
    RunNotFound,
    RunVersions,
    run_dto,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)

PROJECTS = ("atlas", "borealis", "cinder", "delta")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "operation", choices=("create", "resume", "investigate", "source", "finish")
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--item")
    parser.add_argument("--as-of")
    parser.add_argument("--evidence-id")
    args = parser.parse_args()
    try:
        if args.project not in PROJECTS:
            raise ScopeAuthorizationError("project is not configured")
        fields = {"run_id", "item", "as_of", "evidence_id"}
        required: set[str] = {
            "create": set[str](),
            "resume": {"run_id"},
            "investigate": {"run_id", "item", "as_of"},
            "source": {"run_id", "evidence_id"},
            "finish": {"run_id"},
        }[args.operation]
        supplied = {name for name in fields if getattr(args, name) is not None}
        if supplied != required:
            raise ValueError("provide exactly the arguments for this operation")
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            args.project,
            "lab",
            frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE}),
            "run-cli",
        )
        manifest = (
            files("procurement_intelligence_lab.examples")
            .joinpath("corpus_v1/manifest.json")
            .read_bytes()
        )
        versions = RunVersions(
            "fixture",
            "none",
            "pending-agent/v1",
            TOOL_SCHEMA_VERSION,
            sha256(manifest).hexdigest(),
            application_revision(),
        )
        service = AgentRunService(
            SqliteRunStore(args.database), versions=versions, execution_kind=ExecutionKind.FIXTURE
        )
        run = (
            service.start(context=context)
            if args.operation == "create"
            else service.resume(args.run_id, context=context)
        )
        reader = SyntheticCorpusReader()
        tools = CorpusAgentTools(CorpusInvestigationService(reader), reader, service)
        if args.operation == "investigate":
            result = tools.investigate(
                run.run_id,
                InvestigateToolArgs.from_mapping({"item": args.item, "as_of": args.as_of}),
                context=context,
            )
            print(json.dumps({"run": run_dto(run), "result": investigation_dto(result, context)}))
        elif args.operation == "source":
            source = tools.source(
                run.run_id,
                SourceToolArgs.from_mapping({"evidence_id": args.evidence_id}),
                context=context,
            )
            print(json.dumps({"run": run_dto(run), "result": source_dto(source)}))
        elif args.operation == "finish":
            events = service.events(run.run_id, context=context)
            if events[-1].kind != AgentEventKind.RUN_COMPLETED:
                service.record(
                    run.run_id,
                    AgentEventKind.RUN_COMPLETED,
                    parent_id=events[-1].event_id,
                    context=context,
                )
            trajectory = evaluate_trajectory(
                run,
                service.events(run.run_id, context=context),
                required_tools=("investigate_quantity", "inspect_source"),
            )
            print(
                json.dumps(
                    {
                        "run": run_dto(run),
                        "trajectory": asdict(trajectory),
                        "summary": summarize_trajectories((trajectory,)),
                    }
                )
            )
            return 0 if trajectory.outcome == "pass" else 1
        else:
            print(json.dumps(run_dto(run)))
        return 0
    except (
        ScopeAuthorizationError,
        RunNotFound,
        RunStoreError,
        RunConflict,
        ToolExecutionError,
    ) as error:
        code = error.code.value
        category = error.category.value
    except ValueError:
        code = ErrorCode.SEMANTIC_CONTRACT_VIOLATION.value
        category = ErrorCategory.INPUT.value
    print(json.dumps({"code": code, "category": category}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
