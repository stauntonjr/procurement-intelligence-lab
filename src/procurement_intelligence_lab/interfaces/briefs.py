"""Local human review CLI. Fixed demo identity; no model or production authentication."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta
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


def _date(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError("unsupported output field")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("operation", choices=("draft", "show", "review", "save"))
    parser.add_argument("--project", required=True)
    for name in ("run-id", "brief-id", "digest", "idempotency-key", "item", "as-of", "decision"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    try:
        if args.project not in PROJECTS:
            raise ScopeAuthorizationError("project is not configured")
        fields = {"run_id", "brief_id", "digest", "idempotency_key", "item", "as_of", "decision"}
        required = {
            "draft": {"run_id", "item", "as_of"},
            "show": {"run_id", "brief_id"},
            "review": {"run_id", "brief_id", "digest", "decision"},
            "save": {"run_id", "brief_id", "digest", "idempotency_key"},
        }[args.operation]
        if {name for name in fields if getattr(args, name) is not None} != required:
            raise ValueError("provide exactly the arguments for this operation")
        # This separate human shell boundary has review/save authority. Runtime agent root does not.
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            args.project,
            "lab",
            frozenset(
                {Permission.READ_STATE, Permission.READ_EVIDENCE, Permission.REVIEW, Permission.ACT}
            ),
            "human-brief-cli",
        )
        manifest = (
            files("procurement_intelligence_lab.examples")
            .joinpath("corpus_v1/manifest.json")
            .read_bytes()
        )
        runs = AgentRunService(
            SqliteRunStore(args.database),
            versions=RunVersions(
                "fixture",
                "none",
                "pending-agent/v1",
                TOOL_SCHEMA_VERSION,
                sha256(manifest).hexdigest(),
                "package:" + version("procurement-intelligence-lab"),
            ),
            execution_kind=ExecutionKind.FIXTURE,
        )
        reader = SyntheticCorpusReader()
        service = BriefReviewService(
            CorpusAgentTools(CorpusInvestigationService(reader), reader, runs),
            SqliteBriefStore(args.database),
            approval_ttl=timedelta(hours=1),
        )
        if args.operation == "draft":
            data = brief_dto(
                service.draft(
                    args.run_id,
                    InvestigateToolArgs.from_mapping({"item": args.item, "as_of": args.as_of}),
                    context=context,
                )
            )
        elif args.operation == "show":
            data = brief_dto(service.get(args.run_id, args.brief_id, context=context))
        elif args.operation == "review":
            data = asdict(
                service.review(
                    args.run_id, args.brief_id, args.digest, args.decision, context=context
                )
            )
        else:
            data = asdict(
                service.save(
                    args.run_id, args.brief_id, args.digest, args.idempotency_key, context=context
                )
            )
        print(json.dumps(data, default=_date))
        return 0
    except (
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
