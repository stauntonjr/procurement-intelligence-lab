"""Local run-ledger probe with fixed synthetic caller; no live agent execution."""

import argparse
import json
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError, SqliteRunStore
from procurement_intelligence_lab.application.agent_runs import AgentRunService
from procurement_intelligence_lab.platform.semantics.agent_runs import (
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
    parser.add_argument("operation", choices=("create", "resume"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.project not in PROJECTS:
            raise ScopeAuthorizationError("project is not configured")
        if (args.operation == "resume") != bool(args.run_id):
            raise ValueError("resume requires a run ID; create cannot supply one")
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            args.project,
            "lab",
            frozenset({Permission.READ_STATE}),
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
            "run-contract/v1",
            sha256(manifest).hexdigest(),
            "package:" + version("procurement-intelligence-lab"),
        )
        service = AgentRunService(
            SqliteRunStore(args.database), versions=versions, execution_kind=ExecutionKind.FIXTURE
        )
        run = (
            service.start(context=context)
            if args.operation == "create"
            else service.resume(args.run_id, context=context)
        )
        print(json.dumps(run_dto(run)))
        return 0
    except (ScopeAuthorizationError, RunNotFound, RunStoreError, RunConflict) as error:
        code = error.code.value
        category = error.category.value
    except ValueError:
        code = ErrorCode.SEMANTIC_CONTRACT_VIOLATION.value
        category = ErrorCategory.INPUT.value
    print(json.dumps({"code": code, "category": category}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
