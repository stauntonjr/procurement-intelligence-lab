"""Trusted local human document-value review; not an operational-agent tool or authentication service."""

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.application.document_review_payloads import (
    history_payload,
    task_payload,
)
from procurement_intelligence_lab.bootstrap import (
    build_document_review_journal,
    build_document_review_service,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    ReviewOutcome,
    ReviewWorkflow,
    aware,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ReviewContractError,
    ScopeAuthorizationError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewContractError("duplicate review JSON key")
        result[key] = value
    return result


def load_request(path: Path, keys: set[str]) -> dict[str, Any]:
    try:
        if path.stat().st_size > 32000:
            raise ValueError("request limit")
        value: object = json.loads(path.read_text(), object_pairs_hook=_pairs)
        if not isinstance(value, dict):
            raise TypeError("request fields")
        request = cast(dict[str, Any], value)
        if set(request) != keys:
            raise ValueError("request fields")
        for key, item in request.items():
            if key != "proposed_value" and (
                type(item) is not str
                or not item.strip()
                or len(item) > (2000 if key == "reason" else 500)
            ):
                raise ValueError("request text")
        return request
    except (OSError, ValueError, TypeError):
        raise ReviewContractError(
            "review input requires the exact documented JSON fields"
        ) from None


def proposed_value(value: object) -> Decimal | str | None:
    if not isinstance(value, dict):
        raise ReviewContractError("review value requires explicit type and value")
    item = cast(dict[str, object], value)
    if set(item) != {"type", "value"}:
        raise ReviewContractError("review value requires explicit type and value")
    kind, raw = item["type"], item["value"]
    if kind == "null" and raw is None:
        return None
    if kind == "str" and type(raw) is str:
        return raw
    if kind == "decimal" and type(raw) is str:
        try:
            result = Decimal(raw)
            if result.is_finite():
                return result
        except ArithmeticError:
            pass
    raise ReviewContractError(
        "supported BOM review values are finite decimal strings, text or explicit null"
    )


def human_context(scope: StateScope) -> RequestContext:
    actor = os.environ.get("PIL_DOCUMENT_REVIEWER_ID", "")
    if not actor.strip() or len(actor) > 500:
        raise ReviewContractError(
            "configure PIL_DOCUMENT_REVIEWER_ID at the trusted human shell boundary"
        )
    return RequestContext(
        actor,
        scope.tenant_id,
        scope.project_id,
        scope.site_id,
        frozenset({Permission.READ_EVIDENCE, Permission.REVIEW}),
        "document-review-human-cli",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    for name in ("propose", "decide", "show", "history"):
        sub = commands.add_parser(name)
        sub.add_argument("--scope", type=Path, required=True)
        if name in ("propose", "decide"):
            sub.add_argument("--input", type=Path, required=True)
        if name == "show":
            sub.add_argument("--task-id", required=True)
        if name in ("show", "history"):
            sub.add_argument("--as-of")
    args = parser.parse_args()
    try:
        dsn = configured_dsn()
        if args.command == "init":
            build_document_review_journal(dsn).initialize()
            payload: dict[str, object] = {"review_schema_version": 1, "initialized": True}
        else:
            scope = load_scope(args.scope)
            context = human_context(scope)
            service = build_document_review_service(dsn)
            if args.command == "propose":
                request = load_request(
                    args.input,
                    {
                        "request_id",
                        "snapshot_id",
                        "assertion_id",
                        "workflow",
                        "proposed_value",
                        "reason",
                    },
                )
                try:
                    workflow = ReviewWorkflow(request["workflow"])
                except (ValueError, TypeError):
                    raise ReviewContractError("unsupported review workflow") from None
                task = service.propose(
                    scope=scope,
                    request_id=request["request_id"],
                    snapshot_id=request["snapshot_id"],
                    assertion_id=request["assertion_id"],
                    proposed_value=proposed_value(request["proposed_value"]),
                    reason=request["reason"],
                    context=context,
                    workflow=workflow,
                )
                payload = {"task": task_payload(task)}
            elif args.command == "decide":
                request = load_request(
                    args.input, {"request_id", "task_id", "task_digest", "outcome", "reason"}
                )
                try:
                    outcome = ReviewOutcome(request["outcome"])
                except (ValueError, TypeError):
                    raise ReviewContractError("unsupported document-review outcome") from None
                result = service.decide(
                    scope=scope,
                    request_id=request["request_id"],
                    task_id=request["task_id"],
                    task_digest=request["task_digest"],
                    outcome=outcome,
                    reason=request["reason"],
                    context=context,
                )
                payload = history_payload(result)
            else:
                try:
                    as_of = datetime.fromisoformat(args.as_of) if args.as_of is not None else None
                except (ValueError, TypeError):
                    raise ReviewContractError(
                        "review as-of requires an aware ISO timestamp"
                    ) from None
                if as_of is not None:
                    aware(as_of)
                if args.command == "show":
                    payload = history_payload(
                        service.show(scope, args.task_id, context=context, as_of=as_of)
                    )
                else:
                    payload = {
                        "reviews": [
                            history_payload(h)
                            for h in service.history(scope, context=context, as_of=as_of)
                        ]
                    }
    except (SemanticContractError, ScopeAuthorizationError) as error:
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
