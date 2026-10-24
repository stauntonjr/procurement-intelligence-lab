"""Explicit resolved-prefix archive initialization and scoped source-free recovery."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, NoReturn

from procurement_intelligence_lab.application.archived_planned_execution import (
    execution_archive_receipt_payload,
)
from procurement_intelligence_lab.bootstrap import (
    build_resolved_execution_archive,
    build_resolved_execution_archive_reader,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn
from procurement_intelligence_lab.interfaces.assertion_archive import export_content
from procurement_intelligence_lab.interfaces.planned_execution_archive import (
    cursor_value,
    limit_value,
    scope_file,
)
from procurement_intelligence_lab.platform.execution.archive import (
    execution_key,
    history_bounds,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ResolvedExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    SemanticContractError,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ArchiveContractError("invalid resolved archive arguments; use --help")


def receipt_payload(r: ResolvedExecutionArchiveReceipt) -> dict[str, Any]:
    return {
        "receipt_id": r.receipt_id,
        "sequence": r.sequence,
        "execution_digest": r.execution_digest,
        "retained_receipt_digest": r.retained_receipt_digest,
        "scope": vars(r.scope),
        "snapshot_id": r.snapshot_id,
        "prefix_receipt": execution_archive_receipt_payload(r.prefix_receipt),
    }


def main() -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    for command in ("show", "history", "content", "export"):
        sub = commands.add_parser(command)
        sub.add_argument("--scope", type=Path, required=True)
        if command == "history":
            sub.add_argument("--limit", type=limit_value, default=100)
            sub.add_argument("--after-sequence", type=cursor_value, default=0)
        else:
            sub.add_argument("--execution-digest", required=True)
        if command in ("content", "export"):
            sub.add_argument("--output", type=Path, required=True)
    try:
        args = parser.parse_args()
        if args.command == "init":
            build_resolved_execution_archive(configured_dsn()).initialize()
            payload = {"capability": "planned_resolution_prefix/v1", "initialized": True}
        else:
            if args.command != "history":
                execution_key(args.execution_digest)
            scope = scope_file(args.scope)
            if args.command == "history":
                history_bounds(scope, args.limit, args.after_sequence)
            reader = build_resolved_execution_archive_reader(configured_dsn())
            if args.command == "show":
                payload = reader.show(scope, args.execution_digest).as_dict()
            elif args.command == "history":
                page = reader.history(scope, limit=args.limit, after_sequence=args.after_sequence)
                payload = {
                    "receipts": [receipt_payload(r) for r in page.receipts],
                    "has_more": page.has_more,
                    "next_after_sequence": page.next_after_sequence,
                }
            else:
                content = (
                    reader.content(scope, args.execution_digest)
                    if args.command == "content"
                    else reader.export(scope, args.execution_digest)
                )
                export_content(args.output, content)
                payload = {
                    "execution_digest": args.execution_digest,
                    "content_hash": sha256(content).hexdigest(),
                    "byte_length": len(content),
                    "output": str(args.output),
                }
    except SemanticContractError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
