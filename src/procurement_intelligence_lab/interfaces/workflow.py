"""Local fixture checkpoint CLI. No inference or production authentication."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError, SqliteRunStore
from procurement_intelligence_lab.adapters.sqlite_briefs import SqliteBriefStore
from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.application.corpus_agent_tools import (
    TOOL_SCHEMA_VERSION,
    CorpusAgentTools,
    InvestigateToolArgs,
    ToolExecutionError,
)
from procurement_intelligence_lab.application.corpus_investigation import CorpusInvestigationService
from procurement_intelligence_lab.application.exact_brief_review import BriefReviewService
from procurement_intelligence_lab.interfaces.agent_runs import PROJECTS
from procurement_intelligence_lab.platform.semantics.agent_runs import (
    ExecutionKind,
    RunConflict,
    RunNotFound,
    RunVersions,
)
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefIntegrityError,
    BriefNotFound,
    brief_dto,
)
from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.platform.semantics.workflows import (
    WorkflowError,
    WorkflowRequest,
    WorkflowView,
)
from procurement_intelligence_lab.ports.workflows import AgentWorkflowRuntime


@dataclass(frozen=True)
class WorkflowComposition:
    runtime: AgentWorkflowRuntime
    runs: AgentRunService
    service: BriefReviewService
    reader: SyntheticCorpusReader


def compose(database: Path) -> AgentWorkflowRuntime:
    return compose_services(database).runtime


def compose_services(database: Path, *, live_prompt: str | None = None) -> WorkflowComposition:
    # Base install remains dependency-free. Missing optional extra is a typed runtime failure.
    try:
        from procurement_intelligence_lab.adapters.langgraph_review import LangGraphReviewRuntime
    except ImportError as error:
        raise WorkflowError("install the workflow extra") from error
    package = Path(str(files("procurement_intelligence_lab")))
    digest = sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    manifest = (
        files("procurement_intelligence_lab.examples")
        .joinpath("corpus_v1/manifest.json")
        .read_bytes()
    )
    runs = AgentRunService(
        SqliteRunStore(database),
        versions=RunVersions(
            "local-vllm" if live_prompt else "fixture",
            "nvidia/Qwen3.6-35B-A3B-NVFP4" if live_prompt else "none",
            (live_prompt + ":" if live_prompt else "serial-review/v1:")
            + version("langgraph")
            + ":"
            + version("langgraph-checkpoint-sqlite"),
            TOOL_SCHEMA_VERSION,
            sha256(manifest).hexdigest(),
            "sha256:" + digest.hexdigest(),
        ),
        execution_kind=ExecutionKind.LIVE if live_prompt else ExecutionKind.FIXTURE,
    )
    reader = SyntheticCorpusReader()
    service = BriefReviewService(
        CorpusAgentTools(CorpusInvestigationService(reader), reader, runs),
        SqliteBriefStore(database),
    )
    return WorkflowComposition(LangGraphReviewRuntime(service, database), runs, service, reader)


def view_dto(view: WorkflowView) -> dict[str, object]:
    """Explicit allowlist, never return graph events/checkpoint dictionaries."""
    return {
        "run_id": view.run_id,
        "execution_kind": view.brief.run.execution_kind.value,
        "status": view.status,
        "brief": brief_dto(view.brief),
        "saved": asdict(view.saved) if view.saved else None,
    }


def _date(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError("unsupported public output")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("operation", choices=("start", "status", "recover", "review"))
    parser.add_argument("--project", required=True)
    for name in ("run-id", "brief-id", "digest", "decision", "item", "as-of"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    try:
        if args.project not in PROJECTS:
            raise ScopeAuthorizationError("project is not configured")
        fields = {"run_id", "brief_id", "digest", "decision", "item", "as_of"}
        required = {
            "start": {"item", "as_of"},
            "status": {"run_id"},
            "recover": {"run_id"},
            "review": {"run_id", "brief_id", "digest", "decision"},
        }[args.operation]
        if {name for name in fields if getattr(args, name) is not None} != required:
            raise ValueError("provide exactly the arguments for this operation")
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            args.project,
            "lab",
            frozenset(
                {Permission.READ_STATE, Permission.READ_EVIDENCE, Permission.REVIEW, Permission.ACT}
            ),
            "human-workflow-cli",
        )
        runtime = compose(args.database)
        if args.operation == "start":
            request = InvestigateToolArgs.from_mapping(
                {"item": args.item, "as_of": args.as_of}
            ).request
            view = runtime.start(
                WorkflowRequest(request.canonical_key, request.as_of), context=context
            )
        elif args.operation == "status":
            view = runtime.status(args.run_id, context=context)
        elif args.operation == "recover":
            view = runtime.recover(args.run_id, context=context)
        else:
            view = runtime.review(
                args.run_id, args.brief_id, args.digest, args.decision, context=context
            )
        print(json.dumps(view_dto(view), default=_date))
        return 0
    except (
        WorkflowError,
        BriefConflict,
        BriefIntegrityError,
        BriefNotFound,
        RunConflict,
        RunNotFound,
        RunStoreError,
        ToolExecutionError,
        ScopeAuthorizationError,
    ) as error:
        code, category = error.code.value, error.category.value
    except (ValueError, TypeError):
        code, category = ErrorCode.SEMANTIC_CONTRACT_VIOLATION.value, ErrorCategory.INPUT.value
    print(json.dumps({"code": code, "category": category}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
