"""Explicit reviewed source-SKU replay; original source and governing state stay unchanged."""

import json
import sys
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

from procurement_intelligence_lab.bootstrap import build_reviewed_bom_query_service
from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import WORKFLOW
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.interfaces.archived_bom_query import (
    Parser,
    human_context,
    load_execution,
    unique_pairs,
)
from procurement_intelligence_lab.platform.semantics.dependencies import aware, text
from procurement_intelligence_lab.platform.semantics.errors import (
    ScopeAuthorizationError,
    SemanticContractError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext


def load_reviews(path: Path) -> tuple[str, ...]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            raise ValueError("review selection size")
        candidate: object = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
        if type(candidate) is not dict:
            raise ValueError("review selection object")
        data = cast(dict[str, object], candidate)
        if set(data) != {"task_ids"} or type(data["task_ids"]) is not list:
            raise ValueError("review selection shape")
        values = cast(list[object], data["task_ids"])
        if not 1 <= len(values) <= 32:
            raise ValueError("review selection count")
        identities: list[str] = []
        for value in values:
            if type(value) is not str:
                raise ValueError("review task identity type")
            text(value)
            identities.append(value)
        if len(set(identities)) != len(identities):
            raise ValueError("duplicate selection")
        return tuple(sorted(identities))
    except (OSError, ValueError, TypeError, RecursionError, SemanticContractError):
        raise SourceQueryContractError(
            "reviews require bounded Unicode JSON with1..32 unique task_ids"
        ) from None


def reviewed_execution(
    path: Path, snapshot_id: str, task_ids: tuple[str, ...], as_of: datetime
) -> ProvenanceContext:
    source = load_execution(path, snapshot_id)
    digest = sha256(
        json.dumps(
            {
                "source_context_digest": source.config_digest,
                "task_ids": task_ids,
                "as_of": as_of.isoformat(),
                "workflow": WORKFLOW,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return replace(source, workflow_name=WORKFLOW, config_digest=digest)


def main() -> int:
    parser = Parser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--context", type=Path, required=True)
    try:
        args = parser.parse_args()
        try:
            text(args.snapshot_id)
            text(args.request_id)
            as_of = datetime.fromisoformat(args.as_of)
            aware(as_of)
        except (ValueError, SemanticContractError):
            raise SourceQueryContractError(
                "reviewed IDs and fixed-offset as-of are invalid"
            ) from None
        scope = load_scope(args.scope)
        context = human_context(scope)
        task_ids = load_reviews(args.reviews)
        execution = reviewed_execution(args.context, args.snapshot_id, task_ids, as_of)
        payload = (
            build_reviewed_bom_query_service(configured_dsn())
            .execute(
                scope,
                args.snapshot_id,
                args.request_id,
                task_ids,
                as_of,
                execution,
                context=context,
            )
            .as_dict()
        )
    except (SemanticContractError, ScopeAuthorizationError) as error:
        print(json.dumps(error.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
