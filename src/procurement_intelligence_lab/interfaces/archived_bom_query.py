"""Run and register the real distinct-source-SKU producer against one exact archived BOM."""

import argparse
import json
import os
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, NoReturn, cast

from procurement_intelligence_lab.bootstrap import build_archived_bom_query_service
from procurement_intelligence_lab.domains.procurement.source_queries import WORKFLOW
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.platform.semantics.dependencies import text
from procurement_intelligence_lab.platform.semantics.errors import (
    ScopeAuthorizationError,
    SemanticContractError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SourceQueryContractError("invalid archived source query command arguments")


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate context key")
        result[key] = value
    return result


def load_execution(path: Path, snapshot_id: str) -> ProvenanceContext:
    try:
        with path.open("rb") as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            raise ValueError("context size")
        candidate: object = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
        if not isinstance(candidate, dict):
            raise TypeError("context object")
        data = cast(dict[str, Any], candidate)
        if set(data) != {"run_id", "code_revision", "started_at"}:
            raise ValueError("context fields")
        for value in data.values():
            text(value)
        return ProvenanceContext(
            data["run_id"],
            WORKFLOW,
            "1",
            data["code_revision"],
            "local-uncontainerized",
            sha256(
                json.dumps(
                    {"source_snapshot_id": snapshot_id, "run": data},
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            None,
            (snapshot_id,),
            datetime.fromisoformat(data["started_at"]),
        )
    except (OSError, ValueError, TypeError, RecursionError):
        raise SourceQueryContractError(
            "execution context requires bounded Unicode JSON with run_id/code_revision/aware started_at"
        ) from None


def human_context(scope: StateScope) -> RequestContext:
    actor = os.environ.get("PIL_DOCUMENT_REVIEWER_ID", "")
    if not actor.strip():
        raise ScopeAuthorizationError("configure trusted local PIL_DOCUMENT_REVIEWER_ID")
    try:
        for value in (actor, scope.tenant_id, scope.project_id, scope.site_id, scope.version):
            text(value)
    except SemanticContractError:
        raise SourceQueryContractError("source query actor/scope identities are invalid") from None
    return RequestContext(
        actor,
        scope.tenant_id,
        scope.project_id,
        scope.site_id,
        frozenset({Permission.READ_EVIDENCE, Permission.REVIEW}),
        "archived-source-query-cli",
    )


def main() -> int:
    parser = Parser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--context", type=Path, required=True)
    try:
        args = parser.parse_args()
        try:
            text(args.snapshot_id)
            text(args.request_id)
        except SemanticContractError:
            raise SourceQueryContractError("source query identities are invalid") from None
        scope = load_scope(args.scope)
        context = human_context(scope)
        execution = load_execution(args.context, args.snapshot_id)
        result = build_archived_bom_query_service(configured_dsn()).execute(
            scope, args.snapshot_id, args.request_id, execution, context=context
        )
        payload = result.as_dict()
    except (SemanticContractError, ScopeAuthorizationError) as error:
        print(json.dumps(error.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
