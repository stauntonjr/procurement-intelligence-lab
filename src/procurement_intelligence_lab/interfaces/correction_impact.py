"""Trusted local dependency registration and read-only impact; not execution or production authentication."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from procurement_intelligence_lab.application.correction_impact import snapshot_payload
from procurement_intelligence_lab.bootstrap import (
    archive_codec,
    build_correction_impact_service,
    build_dependency_store,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.platform.semantics.dependencies import DependencyManifest, text
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyContractError,
    ScopeAuthorizationError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)

MAX_INPUT_BYTES = 1024 * 1024


def load_manifest(path: Path) -> DependencyManifest:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("oversized producer manifest")
        result = archive_codec().loads(raw.decode("utf-8"))
        if type(result) is not DependencyManifest:
            raise ValueError("expected producer manifest")
        return result
    except (OSError, ValueError, RecursionError):
        raise DependencyContractError(
            "producer input requires a bounded registered typed DependencyManifest"
        ) from None


def human_context(scope: StateScope, *, write: bool) -> RequestContext:
    actor = os.environ.get("PIL_DOCUMENT_REVIEWER_ID", "")
    if not actor.strip():
        raise ScopeAuthorizationError("configure the trusted local PIL_DOCUMENT_REVIEWER_ID")
    for value in (actor, scope.tenant_id, scope.project_id, scope.site_id, scope.version):
        text(value)
    permissions = {Permission.READ_EVIDENCE}
    if write:
        permissions.add(Permission.REVIEW)
    return RequestContext(
        actor,
        scope.tenant_id,
        scope.project_id,
        scope.site_id,
        frozenset(permissions),
        "correction-impact-cli",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    register = commands.add_parser("register")
    register.add_argument("--scope", type=Path, required=True)
    register.add_argument("--input", type=Path, required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--scope", type=Path, required=True)
    inspect.add_argument("--snapshot-id", required=True)
    inspect.add_argument("--task-id", required=True)
    inspect.add_argument("--as-of", required=True)
    inspect.add_argument("--max-depth", type=int, default=8)
    args = parser.parse_args()
    try:
        dsn = configured_dsn()
        if args.command == "init":
            build_dependency_store(dsn).initialize()
            payload = {"dependency_schema_version": 1, "initialized": True}
        else:
            scope = load_scope(args.scope)
            context = human_context(scope, write=args.command == "register")
            service = build_correction_impact_service(dsn)
            if args.command == "register":
                manifest = load_manifest(args.input)
                if manifest.scope != scope:
                    raise ScopeAuthorizationError(
                        "producer manifest differs from requested exact scope/version"
                    )
                payload = snapshot_payload(service.register(manifest, context=context))
            else:
                try:
                    as_of = datetime.fromisoformat(args.as_of)
                except ValueError:
                    raise DependencyContractError(
                        "impact as-of requires an aware ISO timestamp"
                    ) from None
                payload = service.inspect(
                    scope,
                    args.snapshot_id,
                    args.task_id,
                    as_of=as_of,
                    max_depth=args.max_depth,
                    context=context,
                )
    except (SemanticContractError, ScopeAuthorizationError) as error:
        print(json.dumps(error.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
