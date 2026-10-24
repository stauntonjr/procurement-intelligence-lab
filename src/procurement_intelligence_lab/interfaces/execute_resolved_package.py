"""Explicit opt-in six-stage execution with pinned local candidate evidence."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from procurement_intelligence_lab.bootstrap import (
    build_planned_resolved_bom_archive_service,
    build_planned_resolved_bom_service,
    build_resolved_execution_archive,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn
from procurement_intelligence_lab.interfaces.execute_package import Parser, policy, read, request
from procurement_intelligence_lab.interfaces.resolution_inputs import (
    resolution_policy,
    resolved_request,
)
from procurement_intelligence_lab.platform.planning.contracts import PlanningError
from procurement_intelligence_lab.platform.planning.inputs import load_config, load_registry
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    SemanticTypeContractError,
)


def main() -> int:
    parser = Parser(
        description="Execute an explicit six-stage prefix; later stages remain not executed."
    )
    parser.add_argument("source", type=Path)
    for name in (
        "manifest",
        "registry",
        "config",
        "context",
        "normalization-policy",
        "resolution-policy",
        "candidate-snapshot",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--stop-after", choices=("RESOLVE",), required=True)
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Atomically retain the completed prefix and source evidence",
    )
    try:
        args = parser.parse_args()
        manifest = read(args.manifest, 1048576)
        registry = load_registry(read(args.registry, 1048576))
        config = load_config(read(args.config, 1048576))
        prefix = request(args.source, read(args.context, 32768))
        parameters = policy(read(args.normalization_policy, 32768))
        resolution = resolution_policy(read(args.resolution_policy, 32768))
        q = resolved_request(prefix, read(args.candidate_snapshot, 32768), resolution)
        if args.archive:
            service = build_planned_resolved_bom_archive_service(
                manifest=manifest,
                registry=registry,
                config=config,
                normalization_policy=parameters,
                resolution_policy=resolution,
                candidate_input=q.candidate_input,
                clock=lambda: datetime.now(UTC),
                archive_factory=lambda: build_resolved_execution_archive(configured_dsn()),
            )
        else:
            service = build_planned_resolved_bom_service(
                manifest=manifest,
                registry=registry,
                config=config,
                normalization_policy=parameters,
                resolution_policy=resolution,
                candidate_input=q.candidate_input,
                clock=lambda: datetime.now(UTC),
            )
        result = service.execute(q).as_dict()
    except (SemanticContractError, SemanticTypeContractError) as exc:
        error: dict[str, object] = dict(exc.as_dict())
        if isinstance(exc, PlanningError):
            error["issues"] = [
                {"code": i.code, "path": i.path, "message": i.message} for i in exc.issues
            ]
        print(json.dumps(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
