"""Invoke one explicit RECONCILE operation over already-retained RESOLVE producers."""

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from procurement_intelligence_lab.application.archived_reconciliation import (
    RetainedReconciliationResult,
)
from procurement_intelligence_lab.bootstrap import (
    build_archived_reconciliation_service,
    build_retained_reconciliation_service,
)
from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    load_bom_authority,
    timestamp,
)
from procurement_intelligence_lab.interfaces.execute_package import read
from procurement_intelligence_lab.interfaces.reconciliation_inputs import (
    deployment_digest,
    operation_context,
    reconciliation_policy,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.planning.contracts import PlanningError
from procurement_intelligence_lab.platform.planning.inputs import load_config, load_registry
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionError,
    SemanticContractError,
    SemanticTypeContractError,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise PackageExecutionError("invalid reconciliation arguments; use --help")


def main() -> int:
    parser = Parser(description=__doc__)
    for name in ("context", "manifest", "registry", "config", "governing-policy", "authority"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--producer-digest", action="append", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--archive", action="store_true")
    scope = None
    digests: tuple[str, ...] = ()
    try:
        args = parser.parse_args()
        digests = tuple(v for v in args.producer_digest if re.fullmatch("[0-9a-f]{64}", v))
        admit(
            len(digests) == len(args.producer_digest)
            and 1 <= len(digests) <= 8
            and len(set(digests)) == len(digests)
        )
        manifest = read(args.manifest, 1048576)
        registry = load_registry(read(args.registry, 1048576))
        config = load_config(read(args.config, 1048576))
        policy = reconciliation_policy(read(args.governing_policy, 32768))
        authority = load_bom_authority(read(args.authority, 65536))
        plan = plan_manifest(manifest, registry=registry, config=config)
        scope, context = operation_context(
            read(args.context, 32768),
            config_digest=deployment_digest(plan, registry, policy.evidence, authority.evidence),
        )
        as_of = timestamp(args.as_of)
        kwargs: dict[str, Any] = {
            "manifest": manifest,
            "registry": registry,
            "config": config,
            "policy": policy.evidence,
            "authority": authority.evidence,
            "dsn": os.environ.get("PIL_ASSERTION_ARCHIVE_DSN"),
            "clock": lambda: datetime.now(UTC),
        }
        if args.archive:
            result = build_archived_reconciliation_service(**kwargs).execute(
                scope=scope, as_of=as_of, context=context, producer_digests=digests
            )
        else:
            receipt = build_retained_reconciliation_service(**kwargs).execute(
                scope=scope, as_of=as_of, context=context, producer_digests=digests
            )
            result = RetainedReconciliationResult(receipt, None)
        payload = result.as_dict()
    except (SemanticContractError, SemanticTypeContractError) as exc:
        error: dict[str, Any] = dict(exc.as_dict())
        if isinstance(exc, PlanningError):
            error["message"] = "reconciliation deployment metadata is invalid"
            error["issues"] = [{"code": i.code} for i in exc.issues]
        if scope is not None:
            error["scope"] = vars(scope)
        error["producer_recovery"] = [
            {
                "execution_digest": d,
                "module": "procurement_intelligence_lab.interfaces.resolved_execution_archive",
                "scope_argument": "<scope.json>",
                "operations": ["show", "content", "export"],
            }
            for d in dict.fromkeys(digests)
            if len(digests) <= 8
        ]
        print(json.dumps(error, ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
